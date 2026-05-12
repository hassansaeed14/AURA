from __future__ import annotations

import json
import re
import textwrap
import zipfile
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterable, Optional
from uuid import uuid4
from xml.sax.saxutils import escape as xml_escape

import requests
from bs4 import BeautifulSoup
from PIL import Image
from PyPDF2 import PdfReader

from agents.integration.youtube_agent import MetadataService, normalize_youtube_url
from brain.response_engine import clean_response
from tools.document_generator import (
    GENERATED_DIR,
    cleanup_generated_documents,
    generate_document,
    normalize_citation_style,
    normalize_document_formats,
    normalize_document_style,
)


CONTENT_SOURCE_DIR = GENERATED_DIR / "sources"
DEFAULT_SOURCE_RETENTION_HOURS = 24
TEXT_SOURCE_EXTENSIONS = {".txt", ".md", ".json", ".csv", ".html", ".htm", ".py", ".js", ".css"}
IMAGE_SOURCE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}
DOCX_SOURCE_EXTENSIONS = {".docx"}
PDF_SOURCE_EXTENSIONS = {".pdf"}
URL_PATTERN = re.compile(r"https?://\S+", re.IGNORECASE)
FORMAT_ALIAS_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\b(docx|word)\b", "docx"),
    (r"\b(pdf)\b", "pdf"),
    (r"\b(txt|text file|plain text|text)\b", "txt"),
    (r"\b(pptx|ppt|slides?|presentation|slide deck)\b", "pptx"),
)
TRANSFORM_VERBS = (
    "convert",
    "turn",
    "make",
    "generate",
    "create",
    "summarize",
    "transform",
    "rewrite",
)
CONTENT_SESSION_CACHE: dict[str, "ContentSource"] = {}
CONTENT_SOURCE_CACHE: dict[str, "ContentSource"] = {}
CONTENT_TRANSFORM_SESSION_CACHE: dict[str, "ContentTransformRequest"] = {}


@dataclass(slots=True)
class ContentSource:
    source_id: str
    session_id: str
    source_type: str
    title: str
    topic: str
    extracted_text: str
    preview_text: str
    original_name: Optional[str] = None
    file_path: Optional[str] = None
    source_url: Optional[str] = None
    metadata: dict[str, Any] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "session_id": self.session_id,
            "source_type": self.source_type,
            "title": self.title,
            "topic": self.topic,
            "preview_text": self.preview_text,
            "original_name": self.original_name,
            "file_path": self.file_path,
            "source_url": self.source_url,
            "metadata": dict(self.metadata or {}),
        }


@dataclass(slots=True)
class ContentTransformRequest:
    mode: str
    document_type: str
    requested_formats: tuple[str, ...]
    page_target: Optional[int]
    style: str
    include_references: bool
    citation_style: Optional[str]
    include_diagram: bool = False


def _remember_transform_request(session_id: Optional[str], request: ContentTransformRequest) -> None:
    CONTENT_TRANSFORM_SESSION_CACHE[_normalize_session_id(session_id)] = request


def _get_transform_request(session_id: Optional[str]) -> Optional[ContentTransformRequest]:
    return CONTENT_TRANSFORM_SESSION_CACHE.get(_normalize_session_id(session_id))


def ensure_content_source_dir() -> Path:
    CONTENT_SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    return CONTENT_SOURCE_DIR


def cleanup_content_sources(*, max_age_hours: int = DEFAULT_SOURCE_RETENTION_HOURS) -> int:
    directory = ensure_content_source_dir()
    deleted = 0
    cutoff = datetime.now() - timedelta(hours=max(1, int(max_age_hours)))
    for path in directory.iterdir():
        if not path.is_file():
            continue
        try:
            modified = datetime.fromtimestamp(path.stat().st_mtime)
            if modified < cutoff:
                path.unlink(missing_ok=True)
                deleted += 1
        except Exception:
            continue
    return deleted


def _normalize_session_id(session_id: Optional[str]) -> str:
    normalized = re.sub(r"[^A-Za-z0-9._:-]+", "-", str(session_id or "").strip())
    normalized = normalized[:120].strip("-")
    return normalized or "default"


def _clean_text(value: Any) -> str:
    text = str(value or "").replace("\r\n", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _clean_preview(text: str, limit: int = 240) -> str:
    cleaned = _clean_text(text)
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3].rsplit(" ", 1)[0].rstrip(" ,.;:") + "..."


def _split_sentences(text: str) -> list[str]:
    cleaned = _clean_text(text)
    if not cleaned:
        return []
    sentences = [segment.strip() for segment in re.split(r"(?<=[.!?])\s+", cleaned) if segment.strip()]
    if sentences:
        return sentences
    return [cleaned]


def _split_paragraphs(text: str) -> list[str]:
    cleaned = str(text or "").replace("\r\n", "\n")
    return [paragraph.strip() for paragraph in re.split(r"\n\s*\n+", cleaned) if paragraph.strip()]


def _normalize_topic_label(value: str) -> str:
    cleaned = _clean_text(value)
    cleaned = re.sub(r"[_\-]+", " ", cleaned)
    cleaned = re.sub(r"\b(?:this|attached|uploaded|source|file|document|pdf|docx|image|screenshot|video)\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .,!?:;-")
    return cleaned or "Provided Content"


def _extract_topic_from_prompt(prompt: str) -> Optional[str]:
    match = re.search(r"\b(?:on|about|for)\s+(.+)$", str(prompt or ""), flags=re.IGNORECASE)
    if not match:
        return None
    candidate = match.group(1)
    candidate = re.sub(
        r"\b(?:as|in|with|into)\b.+$",
        "",
        candidate,
        flags=re.IGNORECASE,
    )
    normalized = _normalize_topic_label(candidate)
    return normalized or None


def _build_topic_label(topic: str) -> str:
    words = re.findall(r"[A-Za-z0-9]+", str(topic or ""))
    if not words:
        return "Content"
    stop_words = {"a", "an", "and", "for", "in", "of", "on", "the", "to", "with"}
    meaningful = [word for word in words if word.lower() not in stop_words] or words
    if len(meaningful) >= 2:
        acronym = "".join(word[0].upper() for word in meaningful[:4])
        if 2 <= len(acronym) <= 6:
            return acronym
    if len(meaningful) == 1:
        return meaningful[0][:18].title()
    return "".join(word[:1].upper() + word[1:].lower() for word in meaningful[:2])[:22] or "Content"


def _safe_filename(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", str(name or "").strip())
    cleaned = cleaned.strip(".-")
    return cleaned[:80] or f"source-{uuid4().hex[:6]}"


def _store_source(source: ContentSource) -> ContentSource:
    CONTENT_SOURCE_CACHE[source.source_id] = source
    CONTENT_SESSION_CACHE[source.session_id] = source
    return source


def get_latest_content_source(session_id: Optional[str]) -> Optional[ContentSource]:
    return CONTENT_SESSION_CACHE.get(_normalize_session_id(session_id))


def get_content_source(session_id: Optional[str], source_id: Optional[str] = None) -> Optional[ContentSource]:
    normalized_session = _normalize_session_id(session_id)
    if source_id:
        source = CONTENT_SOURCE_CACHE.get(str(source_id))
        if source and source.session_id == normalized_session:
            return source
    return CONTENT_SESSION_CACHE.get(normalized_session)


def _extract_text_from_docx(path: Path) -> str:
    with zipfile.ZipFile(path, "r") as archive:
        xml_bytes = archive.read("word/document.xml")
    xml_text = xml_bytes.decode("utf-8", errors="ignore")
    xml_text = re.sub(r"</w:p>", "\n\n", xml_text)
    xml_text = re.sub(r"</w:tr>", "\n", xml_text)
    xml_text = re.sub(r"<[^>]+>", "", xml_text)
    return _clean_text(xml_text)


def _extract_text_from_pdf(path: Path) -> str:
    with path.open("rb") as handle:
        reader = PdfReader(handle)
        chunks: list[str] = []
        for page in reader.pages[:20]:
            extracted = page.extract_text() or ""
            if extracted.strip():
                chunks.append(extracted)
    return _clean_text("\n\n".join(chunks))


def _extract_text_from_text_file(path: Path) -> str:
    try:
        return _clean_text(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError:
        return _clean_text(path.read_text(encoding="latin-1"))


def _extract_image_summary(path: Path) -> tuple[str, dict[str, Any]]:
    with Image.open(path) as image:
        width, height = image.size
        mode = image.mode
    label = _normalize_topic_label(path.stem)
    source_type = "screenshot" if "screen" in path.stem.lower() else "image"
    summary = clean_response(
        f"""Visual Overview
- Source type: {source_type.title()}
- File label: {label}
- Image dimensions: {width} x {height}
- Color mode: {mode}

Visual Notes
- This uploaded image can be transformed into notes, slides, or an assignment using its visible topic, layout, and any user-provided context.
- If the image is a screenshot or diagram, focus on the main labels, interface areas, flow, and high-level purpose.
- If the user asks for a visual summary, convert the key ideas into short bullets and a simple diagram asset."""
    )
    return summary, {"width": width, "height": height, "mode": mode, "visual_type": source_type}


def _fetch_youtube_description(url: str) -> str:
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except Exception:
        return ""
    soup = BeautifulSoup(response.text, "html.parser")
    for property_name in ("og:description", "twitter:description", "description"):
        node = soup.find("meta", attrs={"property": property_name}) or soup.find("meta", attrs={"name": property_name})
        content = str(node.get("content") or "").strip() if node else ""
        if content:
            return content
    return ""


def _extract_youtube_source(url: str, *, session_id: str) -> ContentSource:
    normalized_url = normalize_youtube_url(url)
    if not normalized_url:
        raise ValueError("Invalid YouTube URL.")
    metadata = MetadataService().fetch(normalized_url)
    description = _fetch_youtube_description(normalized_url)
    transcript_or_fallback = description or (
        f"This source uses YouTube metadata fallback for the video titled {metadata.title} from {metadata.channel}. "
        "A direct transcript was not available, so the transformation engine should rely on the title, channel context, and metadata description."
    )
    extracted_text = clean_response(
        f"""Video Title
{metadata.title}

Channel
{metadata.channel}

Video Summary Source
{transcript_or_fallback}

Study Focus
- Extract the main teaching points, arguments, demonstrations, or takeaways from the available video information.
- When creating notes or slides, prioritize the video's likely core lesson and practical relevance."""
    )
    source = ContentSource(
        source_id=f"src-{uuid4().hex[:12]}",
        session_id=session_id,
        source_type="youtube",
        title=metadata.title,
        topic=_normalize_topic_label(metadata.title),
        extracted_text=extracted_text,
        preview_text=_clean_preview(transcript_or_fallback),
        source_url=normalized_url,
        metadata={"channel": metadata.channel, "video_id": metadata.video_id},
    )
    return _store_source(source)


def register_text_source(text: str, *, session_id: Optional[str], title: Optional[str] = None) -> ContentSource:
    normalized_session = _normalize_session_id(session_id)
    cleaned = _clean_text(text)
    if not cleaned:
        raise ValueError("Text content is required.")
    inferred_title = title or _extract_topic_from_prompt(cleaned) or cleaned.splitlines()[0][:80]
    topic = _normalize_topic_label(inferred_title)
    source = ContentSource(
        source_id=f"src-{uuid4().hex[:12]}",
        session_id=normalized_session,
        source_type="text",
        title=topic,
        topic=topic,
        extracted_text=cleaned,
        preview_text=_clean_preview(cleaned),
        metadata={"length": len(cleaned)},
    )
    return _store_source(source)


def store_uploaded_source(
    *,
    session_id: Optional[str],
    filename: str,
    data: bytes,
    content_type: Optional[str] = None,
) -> ContentSource:
    normalized_session = _normalize_session_id(session_id)
    if not data:
        raise ValueError("Uploaded file is empty.")
    cleanup_content_sources()
    directory = ensure_content_source_dir()
    original_name = Path(filename or "upload").name
    extension = Path(original_name).suffix.lower()
    safe_name = _safe_filename(Path(original_name).stem)
    stored_path = directory / f"{safe_name}-{uuid4().hex[:6]}{extension or '.bin'}"
    stored_path.write_bytes(data)

    metadata: dict[str, Any] = {"content_type": content_type or "", "size_bytes": len(data)}
    if extension in TEXT_SOURCE_EXTENSIONS:
        extracted_text = _extract_text_from_text_file(stored_path)
        source_type = "text"
    elif extension in PDF_SOURCE_EXTENSIONS:
        extracted_text = _extract_text_from_pdf(stored_path)
        source_type = "pdf"
    elif extension in DOCX_SOURCE_EXTENSIONS:
        extracted_text = _extract_text_from_docx(stored_path)
        source_type = "docx"
    elif extension in IMAGE_SOURCE_EXTENSIONS:
        extracted_text, image_meta = _extract_image_summary(stored_path)
        metadata.update(image_meta)
        source_type = str(image_meta.get("visual_type") or "image")
    else:
        raise ValueError("Unsupported file type. Use text, pdf, docx, or image files.")

    if not extracted_text:
        extracted_text = f"Source file: {original_name}"

    topic = _normalize_topic_label(Path(original_name).stem)
    source = ContentSource(
        source_id=f"src-{uuid4().hex[:12]}",
        session_id=normalized_session,
        source_type=source_type,
        title=topic,
        topic=topic,
        extracted_text=extracted_text,
        preview_text=_clean_preview(extracted_text),
        original_name=original_name,
        file_path=str(stored_path),
        metadata=metadata,
    )
    return _store_source(source)


def resolve_or_register_source(
    *,
    session_id: Optional[str],
    source_id: Optional[str] = None,
    source_text: Optional[str] = None,
    source_url: Optional[str] = None,
) -> Optional[ContentSource]:
    if source_text and str(source_text).strip():
        return register_text_source(source_text, session_id=session_id)
    if source_url and str(source_url).strip():
        normalized_url = normalize_youtube_url(source_url)
        if normalized_url:
            return _extract_youtube_source(normalized_url, session_id=_normalize_session_id(session_id))
    return get_content_source(session_id, source_id)


def _detect_youtube_url(prompt: str) -> Optional[str]:
    for match in URL_PATTERN.findall(str(prompt or "")):
        normalized = normalize_youtube_url(match)
        if normalized:
            return normalized
    return None


def _parse_requested_formats(prompt: str, *, mode: str) -> tuple[str, ...]:
    normalized = str(prompt or "").lower()
    matches: list[str] = []
    for pattern, format_name in FORMAT_ALIAS_PATTERNS:
        if re.search(pattern, normalized, flags=re.IGNORECASE) and format_name not in matches:
            matches.append(format_name)
    wants_slides = "pptx" in matches or bool(re.search(r"\b(slides?|presentation|pptx|ppt|slide deck)\b", normalized))
    if wants_slides and not matches:
        matches.append("pptx")
    if not matches:
        return ("pptx",) if mode == "slides" else ("txt",)
    if wants_slides and mode != "slides" and "pptx" not in matches:
        matches.append("pptx")
    return normalize_document_formats(matches)


def _parse_transform_mode(prompt: str) -> str:
    normalized = str(prompt or "").lower()
    if re.search(r"\b(diagram|mind ?map|flow ?chart|visual bullets?|visual summary|visualize)\b", normalized):
        return "diagram"
    if re.search(r"\b(slides?|presentation|pptx|ppt|slide deck)\b", normalized):
        if re.search(r"\b(notes?|summary|assignment)\b", normalized):
            return "notes"
        return "slides"
    if re.search(r"\bassignment\b", normalized):
        return "assignment"
    if re.search(r"\b(summary|summarize)\b", normalized):
        return "summary"
    if re.search(r"\b(notes?|study notes?)\b", normalized):
        return "notes"
    return "notes"


def _parse_transform_style(prompt: str, *, default: str = "professional") -> str:
    normalized = str(prompt or "").lower()
    for style_name in ("detailed", "simple", "professional"):
        if re.search(rf"\b{style_name}\b", normalized):
            return style_name
    return default


def _parse_page_target(prompt: str) -> Optional[int]:
    match = re.search(r"\b(\d{1,2})\s*(?:page|pages)\b", str(prompt or "").lower())
    if not match:
        return None
    return max(1, min(int(match.group(1)), 20))


def _parse_include_references(prompt: str) -> bool:
    return bool(re.search(r"\b(reference|references|bibliography|works cited|citation|citations)\b", str(prompt or "").lower()))


def _parse_citation_style(prompt: str) -> Optional[str]:
    normalized = str(prompt or "").lower()
    for style_name in ("apa", "mla", "chicago", "harvard", "ieee", "basic"):
        if re.search(rf"\b{style_name}\b", normalized):
            return style_name
    return None


def is_content_transform_prompt(prompt: str, *, has_source: bool = False) -> bool:
    normalized = str(prompt or "").strip().lower()
    if not normalized:
        return False
    if _detect_youtube_url(normalized):
        return True
    if any(verb in normalized for verb in TRANSFORM_VERBS):
        if re.search(r"\b(notes?|assignment|summary|slides?|presentation|pptx|ppt|diagram|mind ?map|flow ?chart)\b", normalized):
            return True
        if has_source and re.search(r"\b(this|it|attached|uploaded|file|pdf|docx|image|screenshot|video)\b", normalized):
            return True
    if has_source and re.search(r"\b(this|attached|uploaded)\b", normalized) and re.search(r"\b(notes?|assignment|summary|slides?|diagram)\b", normalized):
        return True
    if re.search(r"\bconvert video to\b", normalized):
        return True
    return False


def _detect_followup_controls(prompt: str) -> dict[str, Any]:
    normalized = str(prompt or "").strip().lower()
    requested_formats = []
    for pattern, format_name in FORMAT_ALIAS_PATTERNS:
        if re.search(pattern, normalized, flags=re.IGNORECASE) and format_name not in requested_formats:
            requested_formats.append(format_name)

    stripped = normalized
    stripped = re.sub(r"^(?:please\s+)?", "", stripped)
    stripped = re.sub(r"\b(?:also|and|as|in|export|download|save|it|make|give|me|another|format|version|turn|convert|transform|with)\b", " ", stripped)
    stripped = re.sub(r"\b(?:notes?|assignment|summary|slides?|presentation|pptx|ppt|diagram|mind ?map|flow ?chart)\b", " ", stripped)
    stripped = re.sub(r"\b(?:professional|simple|detailed)\b", " ", stripped)
    stripped = re.sub(r"\b(?:reference|references|bibliography|works cited|citation|citations)\b", " ", stripped)
    stripped = re.sub(r"\b(?:apa|mla|chicago|harvard|ieee|basic)\b", " ", stripped)
    stripped = re.sub(r"\b\d{1,2}\s*(?:page|pages)\b", " ", stripped)
    for pattern, _ in FORMAT_ALIAS_PATTERNS:
        stripped = re.sub(pattern, " ", stripped, flags=re.IGNORECASE)
    stripped = re.sub(r"[^a-z0-9]+", " ", stripped)
    stripped = re.sub(r"\s+", " ", stripped).strip()

    style_match = next((style_name for style_name in ("detailed", "simple", "professional") if re.search(rf"\b{style_name}\b", normalized)), None)
    return {
        "requested_formats": normalize_document_formats(requested_formats) if requested_formats else (),
        "page_target": _parse_page_target(normalized),
        "style": style_match,
        "include_references": _parse_include_references(normalized),
        "citation_style": _parse_citation_style(normalized),
        "include_diagram": bool(re.search(r"\b(diagram|mind ?map|flow ?chart|visual)\b", normalized)),
        "looks_like_followup": bool(
            requested_formats
            or style_match is not None
            or _parse_page_target(normalized) is not None
            or _parse_include_references(normalized)
            or _parse_citation_style(normalized) is not None
            or re.search(r"\b(diagram|mind ?map|flow ?chart|visual)\b", normalized)
        ) and not stripped,
    }


def _build_source_outline(source: ContentSource) -> list[tuple[str, list[str]]]:
    paragraphs = _split_paragraphs(source.extracted_text)
    if not paragraphs:
        return [("Overview", ["No readable source content was extracted."])]

    sections: list[tuple[str, list[str]]] = []
    title_taken = False
    for paragraph in paragraphs[:10]:
        lines = [line.strip() for line in paragraph.splitlines() if line.strip()]
        if not lines:
            continue
        first_line = lines[0]
        if not title_taken and len(first_line) <= 80 and not first_line.endswith("."):
            title_taken = True
            heading = _normalize_topic_label(first_line)
            body = [_clean_text(" ".join(lines[1:]))] if len(lines) > 1 else []
            sections.append((heading or "Overview", [entry for entry in body if entry]))
            continue
        heading = "Overview" if not sections else f"Section {len(sections) + 1}"
        sections.append((heading, [_clean_text(" ".join(lines))]))
    return sections or [("Overview", [paragraphs[0]])]


def _select_key_points(source: ContentSource, *, limit: int = 8) -> list[str]:
    points: list[str] = []
    for sentence in _split_sentences(source.extracted_text):
        cleaned = sentence.strip(" -•")
        if cleaned and cleaned not in points:
            points.append(cleaned)
        if len(points) >= limit:
            break
    return points or [source.preview_text or f"Key ideas from {source.title}."]


def _build_notes_from_source(source: ContentSource, request: ContentTransformRequest) -> str:
    points = _select_key_points(source, limit=10 if request.style == "detailed" else 7 if request.style == "professional" else 5)
    overview = points[:2]
    core_points = points[2:6] or points[:4]
    supporting = points[6:] or points[2:4]
    lines = [
        "Overview",
        *[f"- {item}" for item in overview],
        "",
        "Key Ideas",
        *[f"- {item}" for item in core_points],
        "",
        "Important Details",
        *[f"- {item}" for item in supporting],
        "",
        "Summary",
        f"- {source.title} can be understood through its main idea, supporting details, and practical relevance.",
        f"- These notes were transformed from the provided {source.source_type} source so the structure stays aligned with the original material.",
    ]
    if request.style == "detailed":
        lines.extend([
            "",
            "Extended Insight",
            f"- The transformed notes keep the source grounded while organizing the content into revision-friendly sections.",
            f"- Use these notes to move from raw material into study, slides, or assignment writing more quickly.",
        ])
    return clean_response("\n".join(lines))


def _build_assignment_from_source(source: ContentSource, request: ContentTransformRequest) -> str:
    points = _select_key_points(source, limit=12 if request.style == "detailed" else 9)
    source_outline = _build_source_outline(source)
    historical = points[0:2]
    core_points = points[2:5] or points[:3]
    applied_points = points[5:8] or points[2:5]
    limitation_points = points[8:10] or points[4:6]
    conclusion_points = points[-2:] if len(points) >= 2 else points
    paragraphs = [
        "Introduction",
        clean_response(
            f"{source.title} is an important subject because the provided {source.source_type} material highlights its central ideas, context, and practical value. "
            f"This transformed assignment organizes the source into a clearer academic structure so the reader can move from introduction to explanation, application, and conclusion without losing the original meaning."
        ),
        "",
        "Background and Context",
        clean_response(
            f"The source material shows that {source.topic} should be understood within a wider context rather than as an isolated topic. "
            + " ".join(historical)
        ),
        "",
        "Core Concepts",
        clean_response(
            f"The main concepts emerging from the source can be grouped into the core ideas, relationships, and terms that give {source.topic} its meaning. "
            + " ".join(core_points)
        ),
        "",
        "Applications and Practical Relevance",
        clean_response(
            f"A strong assignment should also show how {source.topic} matters in practice. "
            + " ".join(applied_points)
        ),
        "",
        "Challenges and Limitations",
        clean_response(
            "The source also suggests that meaningful discussion requires awareness of limitations, tradeoffs, or implementation concerns. "
            + " ".join(limitation_points)
        ),
    ]
    if request.page_target and request.page_target >= 7:
        paragraphs.extend([
            "",
            "Source-Based Discussion",
            clean_response(
                "When the transformed content is expanded into a longer assignment, the structure should preserve the original source logic while making the discussion more analytical and academic."
            ),
        ])
    paragraphs.extend([
        "",
        "Conclusion",
        clean_response(
            f"In conclusion, {source.topic} can be explained effectively when the original material is reorganized into clearer academic sections. "
            + " ".join(conclusion_points)
        ),
    ])
    if request.include_references:
        citation_label = request.citation_style.upper() if request.citation_style else "BASIC"
        paragraphs.extend([
            "",
            f"References ({citation_label} Style)" if request.citation_style else "References",
            f"- Original source: {source.original_name or source.source_url or source.title}",
            "- Add verified academic references that support and extend the transformed source material.",
        ])
    return clean_response("\n".join(paragraphs))


def _build_diagram_svg(source: ContentSource, request: ContentTransformRequest, topic_label: str) -> dict[str, Any]:
    directory = ensure_content_source_dir()
    base_name = f"{_build_topic_label(topic_label)}-Diagram"
    file_name = f"{base_name}-{uuid4().hex[:4].upper()}.svg"
    path = directory / file_name
    points = _select_key_points(source, limit=5)
    card_height = 72
    svg_height = 180 + (len(points) * 96)
    box_y_positions = [120 + (index * 96) for index in range(len(points))]

    def _card(y: int, title: str, index: int) -> str:
        return (
            f'<rect x="160" y="{y}" rx="18" ry="18" width="560" height="{card_height}" fill="#ffffff" stroke="#3b82f6" stroke-width="2"/>'
            f'<text x="192" y="{y + 28}" font-family="Segoe UI, Arial, sans-serif" font-size="18" font-weight="700" fill="#111827">Point {index + 1}</text>'
            f'<text x="192" y="{y + 52}" font-family="Segoe UI, Arial, sans-serif" font-size="15" fill="#374151">{xml_escape(_clean_preview(title, 92))}</text>'
        )

    connectors = []
    for index, y in enumerate(box_y_positions):
        if index == 0:
            connectors.append(f'<line x1="440" y1="88" x2="440" y2="{y}" stroke="#94a3b8" stroke-width="3"/>')
        else:
            previous_y = box_y_positions[index - 1] + card_height
            connectors.append(f'<line x1="440" y1="{previous_y}" x2="440" y2="{y}" stroke="#94a3b8" stroke-width="3"/>')

    cards = "".join(_card(y, point, index) for index, (y, point) in enumerate(zip(box_y_positions, points)))
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="880" height="{svg_height}" viewBox="0 0 880 {svg_height}">'
        '<rect width="100%" height="100%" fill="#eff6ff"/>'
        '<rect x="140" y="24" rx="24" ry="24" width="600" height="72" fill="#1d4ed8"/>'
        f'<text x="440" y="58" text-anchor="middle" font-family="Segoe UI, Arial, sans-serif" font-size="28" font-weight="700" fill="#ffffff">{xml_escape(source.title)}</text>'
        f'<text x="440" y="82" text-anchor="middle" font-family="Segoe UI, Arial, sans-serif" font-size="14" fill="#dbeafe">{xml_escape(request.mode.title())} Diagram</text>'
        f'{"".join(connectors)}{cards}</svg>'
    )
    path.write_text(svg, encoding="utf-8")
    return {
        "format": "svg",
        "file_name": file_name,
        "file_path": str(path),
        "download_url": f"/downloads/sources/{file_name}",
        "primary": False,
    }


def _augment_delivery_with_assets(payload: dict[str, Any], assets: list[dict[str, Any]]) -> dict[str, Any]:
    if not assets:
        return payload
    files = list(payload.get("files") or [])
    files.extend(assets)
    payload["files"] = files
    requested_formats = list(payload.get("requested_formats") or [])
    for asset in assets:
        format_name = str(asset.get("format") or "").strip().lower()
        if format_name and format_name not in requested_formats:
            requested_formats.append(format_name)
    payload["requested_formats"] = requested_formats
    available_formats = list(payload.get("available_formats") or [])
    for format_name in requested_formats:
        if format_name not in available_formats:
            available_formats.append(format_name)
    payload["available_formats"] = available_formats
    delivery = dict(payload.get("document_delivery") or {})
    delivery["files"] = files
    delivery["requested_formats"] = requested_formats
    delivery["available_formats"] = available_formats
    payload["document_delivery"] = delivery
    if len(files) > 1:
        payload["message"] = "Done. Your content set is ready."
        delivery["delivery_message"] = payload["message"]
    return payload


def _build_transform_request(prompt: str, *, has_source: bool) -> Optional[ContentTransformRequest]:
    if not is_content_transform_prompt(prompt, has_source=has_source):
        return None
    mode = _parse_transform_mode(prompt)
    document_type = "assignment" if mode == "assignment" else "notes"
    requested_formats = _parse_requested_formats(prompt, mode=mode)
    if mode == "slides":
        document_type = "notes"
        requested_formats = ("pptx",)
    page_target = _parse_page_target(prompt)
    style = _parse_transform_style(prompt, default="simple" if mode in {"summary", "slides"} else "professional")
    citation_style = normalize_citation_style(_parse_citation_style(prompt))
    include_references = _parse_include_references(prompt) or citation_style is not None
    include_diagram = bool(re.search(r"\b(diagram|mind ?map|flow ?chart|visual bullets?|visual summary|visualize)\b", str(prompt or "").lower()))
    return ContentTransformRequest(
        mode=mode,
        document_type=document_type,
        requested_formats=requested_formats,
        page_target=page_target,
        style=style,
        include_references=include_references,
        citation_style=citation_style,
        include_diagram=include_diagram,
    )


def resolve_content_transform_request(
    prompt: str,
    *,
    session_id: Optional[str],
    source_id: Optional[str] = None,
    source_text: Optional[str] = None,
    source_url: Optional[str] = None,
) -> Optional[ContentTransformRequest]:
    normalized_session = _normalize_session_id(session_id)
    known_source = get_content_source(normalized_session, source_id) or get_latest_content_source(normalized_session)
    has_source = bool(
        known_source
        or str(source_text or "").strip()
        or str(source_url or "").strip()
        or _detect_youtube_url(prompt)
    )

    transform_request = _build_transform_request(prompt, has_source=has_source)
    if transform_request is not None:
        return transform_request

    previous_request = _get_transform_request(normalized_session)
    if previous_request is None or not has_source:
        return None

    followup_controls = _detect_followup_controls(prompt)
    if not followup_controls.get("looks_like_followup"):
        return None

    return ContentTransformRequest(
        mode=previous_request.mode,
        document_type=previous_request.document_type,
        requested_formats=followup_controls.get("requested_formats") or previous_request.requested_formats,
        page_target=followup_controls.get("page_target") or previous_request.page_target,
        style=normalize_document_style(followup_controls.get("style") or previous_request.style),
        include_references=bool(followup_controls.get("include_references") or previous_request.include_references),
        citation_style=normalize_citation_style(followup_controls.get("citation_style") or previous_request.citation_style),
        include_diagram=bool(followup_controls.get("include_diagram") or previous_request.include_diagram),
    )


def transform_content_request(
    prompt: str,
    *,
    session_id: Optional[str],
    source_id: Optional[str] = None,
    source_text: Optional[str] = None,
    source_url: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    normalized_session = _normalize_session_id(session_id)
    cleanup_content_sources()
    cleanup_generated_documents()

    source = resolve_or_register_source(
        session_id=normalized_session,
        source_id=source_id,
        source_text=source_text,
        source_url=source_url,
    )
    if source is None:
        youtube_url = _detect_youtube_url(prompt)
        if youtube_url:
            source = _extract_youtube_source(youtube_url, session_id=normalized_session)

    transform_request = resolve_content_transform_request(
        prompt,
        session_id=normalized_session,
        source_id=source_id,
        source_text=source_text,
        source_url=source_url,
    )
    if transform_request is None:
        return None

    if source is None:
        topic = _extract_topic_from_prompt(prompt) or _normalize_topic_label(prompt)
        source = register_text_source(
            f"Topic focus: {topic}\n\nThis source was created from the user's prompt so VORIS can transform it into structured output.",
            session_id=normalized_session,
            title=topic,
        )

    topic = _extract_topic_from_prompt(prompt) or source.topic or source.title
    if transform_request.mode == "assignment":
        content = _build_assignment_from_source(source, transform_request)
    else:
        content = _build_notes_from_source(source, transform_request)

    generated = generate_document(
        transform_request.document_type,
        topic,
        transform_request.requested_formats[0],
        formats=transform_request.requested_formats,
        page_target=transform_request.page_target,
        style=transform_request.style,
        include_references=transform_request.include_references,
        citation_style=transform_request.citation_style,
        prebuilt_content=content,
    )
    generated["source_id"] = source.source_id
    generated["source_type"] = source.source_type
    generated["source_preview"] = source.preview_text
    generated["source_title"] = source.title
    _remember_transform_request(normalized_session, transform_request)
    assets: list[dict[str, Any]] = []
    if transform_request.include_diagram or transform_request.mode == "diagram":
        assets.append(_build_diagram_svg(source, transform_request, topic))
    generated = _augment_delivery_with_assets(generated, assets)
    return generated
