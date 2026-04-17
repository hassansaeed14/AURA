from __future__ import annotations

import re
import textwrap
import zipfile
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional
from xml.sax.saxutils import escape as xml_escape

from brain.response_engine import generate_document_content_payload


PROJECT_ROOT = Path(__file__).resolve().parents[1]
GENERATED_DIR = PROJECT_ROOT / "generated"
DEFAULT_RETENTION_HOURS = 24
SUPPORTED_EXPORT_FORMATS = {"txt", "pdf", "docx"}
FORMAT_TOKEN_PATTERN = r"(?:pdf|docx|word|txt|text)"
DOCUMENT_REQUEST_PREFIX = r"^(?:please\s+)?(?:make|create|generate|prepare|give me|write)\b"


@dataclass(slots=True)
class DocumentRequest:
    document_type: str
    topic: str
    export_format: str
    page_target: Optional[int] = None


def ensure_generated_dir() -> Path:
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    return GENERATED_DIR


def cleanup_generated_documents(*, max_age_hours: int = DEFAULT_RETENTION_HOURS) -> int:
    directory = ensure_generated_dir()
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


def normalize_document_format(value: str | None) -> str:
    normalized = str(value or "txt").strip().lower()
    aliases = {
        "text": "txt",
        "word": "docx",
        ".txt": "txt",
        ".pdf": "pdf",
        ".docx": "docx",
    }
    normalized = aliases.get(normalized, normalized)
    if normalized not in SUPPORTED_EXPORT_FORMATS:
        raise ValueError("format must be one of: txt, pdf, docx")
    return normalized


def _normalize_topic(value: str) -> str:
    topic = str(value or "").strip()
    topic = re.sub(r"\s+", " ", topic)
    topic = re.sub(r"\s+(?:in|as)\s+(?:pdf|docx|word|txt|text)\b$", "", topic, flags=re.IGNORECASE)
    return topic.strip(" .,!?:;-")


def _sanitize_slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", str(value or "").strip().lower())
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug[:70] or "document"


def _parse_page_target(text: str) -> Optional[int]:
    match = re.search(r"\b(\d{1,2})\s*(?:page|pages)\b", str(text or "").lower())
    if not match:
        return None
    pages = int(match.group(1))
    return max(1, min(pages, 20))


def _detect_requested_format(text: str) -> Optional[str]:
    lowered = str(text or "").lower()
    if " docx" in lowered or " word" in lowered:
        return "docx"
    if " pdf" in lowered:
        return "pdf"
    if " txt" in lowered or " text file" in lowered or " plain text" in lowered:
        return "txt"
    return None


def detect_document_request(text: str) -> Optional[DocumentRequest]:
    normalized = str(text or "").strip()
    if not normalized:
        return None

    lowered = normalized.lower()
    export_format = _detect_requested_format(lowered) or "txt"
    page_target = _parse_page_target(lowered)
    request_shape = bool(
        re.match(DOCUMENT_REQUEST_PREFIX, lowered, flags=re.IGNORECASE)
        or re.match(rf"^(?:{FORMAT_TOKEN_PATTERN})\s+(?:notes|assignment)\b", lowered, flags=re.IGNORECASE)
        or re.match(r"^(?:notes|assignment)\b", lowered, flags=re.IGNORECASE)
    )
    if not request_shape:
        return None

    explicit_type: Optional[str] = None
    if re.search(r"\bnotes\b", lowered):
        explicit_type = "notes"
    elif re.search(r"\bassignment\b", lowered):
        explicit_type = "assignment"
    elif page_target is not None and re.search(r"\b(?:on|about|for)\b", lowered):
        explicit_type = "assignment"

    if explicit_type is None:
        return None

    topic_match = re.search(r"\b(?:on|about|for)\s+(.+)$", normalized, flags=re.IGNORECASE)
    if not topic_match:
        return None

    topic = _normalize_topic(topic_match.group(1))
    if topic:
        return DocumentRequest(explicit_type, topic, export_format, page_target=page_target)

    return None


def _build_title(document_type: str, topic: str) -> str:
    label = "Notes" if document_type == "notes" else "Assignment"
    return f"{topic.title()} - {label}"


def _document_text(title: str, content: str) -> str:
    cleaned_content = str(content or "").strip()
    return f"{title}\n{'=' * len(title)}\n\n{cleaned_content}\n"


def _wrap_export_lines(text: str, *, width: int = 88) -> list[str]:
    wrapped: list[str] = []
    for raw_line in str(text or "").splitlines():
        if not raw_line.strip():
            wrapped.append("")
            continue
        initial_indent = ""
        subsequent_indent = ""
        stripped = raw_line.lstrip()
        if stripped.startswith(("- ", "* ", "• ")):
            initial_indent = raw_line[: len(raw_line) - len(stripped)]
            subsequent_indent = initial_indent + "  "
        parts = textwrap.wrap(
            raw_line,
            width=width,
            initial_indent=initial_indent,
            subsequent_indent=subsequent_indent,
            break_long_words=False,
            break_on_hyphens=False,
        )
        wrapped.extend(parts or [""])
    return wrapped


def _write_txt(path: Path, title: str, content: str) -> None:
    path.write_text(_document_text(title, content), encoding="utf-8")


def _pdf_escape(value: str) -> str:
    return str(value or "").replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _build_pdf_bytes(title: str, content: str) -> bytes:
    lines = _wrap_export_lines(_document_text(title, content), width=92)
    lines_per_page = 46
    chunks = [lines[index : index + lines_per_page] for index in range(0, len(lines), lines_per_page)] or [[]]

    objects: list[bytes] = []
    font_object_number = 3
    page_object_numbers: list[int] = []

    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(b"<< /Type /Pages /Kids [] /Count 0 >>")
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    for page_lines in chunks:
        stream_lines = ["BT", "/F1 11 Tf", "14 TL", "50 790 Td"]
        for line in page_lines:
            if line:
                stream_lines.append(f"({_pdf_escape(line)}) Tj")
            stream_lines.append("T*")
        stream_lines.append("ET")
        stream_data = "\n".join(stream_lines).encode("utf-8")
        content_object_number = len(objects) + 1
        objects.append(f"<< /Length {len(stream_data)} >>\nstream\n".encode("utf-8") + stream_data + b"\nendstream")

        page_object_number = len(objects) + 1
        page_payload = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 {font_object_number} 0 R >> >> "
            f"/Contents {content_object_number} 0 R >>"
        ).encode("utf-8")
        objects.append(page_payload)
        page_object_numbers.append(page_object_number)

    kids = " ".join(f"{number} 0 R" for number in page_object_numbers)
    objects[1] = f"<< /Type /Pages /Kids [{kids}] /Count {len(page_object_numbers)} >>".encode("utf-8")

    pdf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode("utf-8"))
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")

    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("utf-8"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("utf-8"))
    pdf.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF"
        ).encode("utf-8")
    )
    return bytes(pdf)


def _write_pdf(path: Path, title: str, content: str) -> None:
    path.write_bytes(_build_pdf_bytes(title, content))


def _docx_paragraph_xml(line: str) -> str:
    escaped = xml_escape(str(line or ""))
    return (
        "<w:p>"
        "<w:r><w:t xml:space=\"preserve\">"
        f"{escaped}"
        "</w:t></w:r>"
        "</w:p>"
    )


def _write_docx(path: Path, title: str, content: str) -> None:
    paragraphs = [_docx_paragraph_xml(title), _docx_paragraph_xml("")]
    for line in _document_text("", content).splitlines():
        paragraphs.append(_docx_paragraph_xml(line))

    document_xml = (
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
        "<w:document xmlns:wpc=\"http://schemas.microsoft.com/office/word/2010/wordprocessingCanvas\" "
        "xmlns:mc=\"http://schemas.openxmlformats.org/markup-compatibility/2006\" "
        "xmlns:o=\"urn:schemas-microsoft-com:office:office\" "
        "xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\" "
        "xmlns:m=\"http://schemas.openxmlformats.org/officeDocument/2006/math\" "
        "xmlns:v=\"urn:schemas-microsoft-com:vml\" "
        "xmlns:wp14=\"http://schemas.microsoft.com/office/word/2010/wordprocessingDrawing\" "
        "xmlns:wp=\"http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing\" "
        "xmlns:w10=\"urn:schemas-microsoft-com:office:word\" "
        "xmlns:w=\"http://schemas.openxmlformats.org/wordprocessingml/2006/main\" "
        "xmlns:w14=\"http://schemas.microsoft.com/office/word/2010/wordml\" "
        "xmlns:wpg=\"http://schemas.microsoft.com/office/word/2010/wordprocessingGroup\" "
        "xmlns:wpi=\"http://schemas.microsoft.com/office/word/2010/wordprocessingInk\" "
        "xmlns:wne=\"http://schemas.microsoft.com/office/word/2006/wordml\" "
        "xmlns:wps=\"http://schemas.microsoft.com/office/word/2010/wordprocessingShape\" mc:Ignorable=\"w14 wp14\">"
        "<w:body>"
        f"{''.join(paragraphs)}"
        "<w:sectPr><w:pgSz w:w=\"12240\" w:h=\"15840\"/><w:pgMar w:top=\"1440\" w:right=\"1440\" "
        "w:bottom=\"1440\" w:left=\"1440\" w:header=\"708\" w:footer=\"708\" w:gutter=\"0\"/></w:sectPr>"
        "</w:body>"
        "</w:document>"
    )

    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>"""

    package_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>"""

    core_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
 xmlns:dc="http://purl.org/dc/elements/1.1/"
 xmlns:dcterms="http://purl.org/dc/terms/"
 xmlns:dcmitype="http://purl.org/dc/dcmitype/"
 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>{xml_escape(title)}</dc:title>
  <dc:creator>AURA</dc:creator>
  <cp:lastModifiedBy>AURA</cp:lastModifiedBy>
  <dcterms:created xsi:type="dcterms:W3CDTF">{datetime.utcnow().isoformat()}Z</dcterms:created>
</cp:coreProperties>"""

    app_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
 xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>AURA</Application>
</Properties>"""

    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", package_rels)
        archive.writestr("docProps/core.xml", core_xml)
        archive.writestr("docProps/app.xml", app_xml)
        archive.writestr("word/document.xml", document_xml)


def _build_output_path(document_type: str, topic: str, export_format: str) -> tuple[Path, str]:
    directory = ensure_generated_dir()
    slug = _sanitize_slug(topic)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"{document_type}-{slug}-{timestamp}.{export_format}"
    return directory / filename, filename


def generate_document(
    document_type: str,
    topic: str,
    export_format: str = "txt",
    *,
    page_target: Optional[int] = None,
) -> dict[str, Any]:
    normalized_type = str(document_type or "").strip().lower()
    if normalized_type not in {"notes", "assignment"}:
        raise ValueError("type must be either 'notes' or 'assignment'")

    normalized_topic = _normalize_topic(topic)
    if not normalized_topic:
        raise ValueError("topic is required")

    normalized_format = normalize_document_format(export_format)
    cleanup_generated_documents()

    content_payload = generate_document_content_payload(
        normalized_type,
        normalized_topic,
        page_target=page_target,
    )
    content = str(content_payload.get("content") or "").strip()
    if not content:
        raise RuntimeError("Document generation returned empty content.")

    title = _build_title(normalized_type, normalized_topic)
    output_path, filename = _build_output_path(normalized_type, normalized_topic, normalized_format)

    if normalized_format == "txt":
        _write_txt(output_path, title, content)
    elif normalized_format == "pdf":
        _write_pdf(output_path, title, content)
    else:
        _write_docx(output_path, title, content)

    label = "notes" if normalized_type == "notes" else "assignment"
    plural = "them" if normalized_type == "notes" else "it"
    return {
        "success": True,
        "document_type": normalized_type,
        "topic": normalized_topic,
        "format": normalized_format,
        "page_target": page_target,
        "title": title,
        "file_name": filename,
        "file_path": str(output_path),
        "download_url": f"/downloads/{filename}",
        "content": content,
        "provider": content_payload.get("provider"),
        "model": content_payload.get("model"),
        "source": content_payload.get("source"),
        "degraded": bool(content_payload.get("degraded", False)),
        "providers_tried": list(content_payload.get("providers_tried") or []),
        "message": f"I created the {label} on {normalized_topic}. You can download {plural} here: /downloads/{filename}",
    }
