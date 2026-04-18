"""
Content extraction for AURA's transformation engine.
Normalizes: raw text, .txt, .pdf (text + OCR fallback), .docx, images, YouTube URLs.
"""
from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Optional, Union
from urllib.parse import parse_qs, urlparse


@dataclass(slots=True)
class ExtractedContent:
    text: str
    source_type: str
    source_label: str
    success: bool
    error: Optional[str] = None
    extraction_mode: Optional[str] = None  # "transcript", "metadata", "text", "ocr", "structured"


_YOUTUBE_URL_RE = re.compile(
    r"(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?v=[\w-]+|youtu\.be/[\w-]+|youtube\.com/shorts/[\w-]+)",
    flags=re.IGNORECASE,
)

_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".gif", ".webp"}


def is_youtube_url(value: str) -> bool:
    return bool(_YOUTUBE_URL_RE.search(str(value or "")))


def _extract_video_id(url: str) -> Optional[str]:
    try:
        parsed = urlparse(str(url).strip())
        host = parsed.netloc.lower()
        if host in {"youtube.com", "www.youtube.com", "m.youtube.com"}:
            if parsed.path == "/watch":
                return parse_qs(parsed.query).get("v", [None])[0]
            if parsed.path.startswith(("/shorts/", "/embed/")):
                parts = [p for p in parsed.path.split("/") if p]
                return parts[1] if len(parts) >= 2 else None
        if host == "youtu.be":
            return parsed.path.lstrip("/") or None
        return None
    except Exception:
        return None


def _detect_type(source: Union[str, Path, bytes], filename: Optional[str]) -> str:
    if isinstance(source, bytes):
        if filename:
            ext = Path(filename).suffix.lower()
            if ext == ".pdf":
                return "pdf_bytes"
            if ext == ".docx":
                return "docx_bytes"
            if ext in _IMAGE_EXTENSIONS:
                return "image_bytes"
        return "txt_bytes"
    if isinstance(source, Path):
        ext = source.suffix.lower()
        if ext == ".pdf":
            return "pdf"
        if ext == ".docx":
            return "docx"
        if ext in _IMAGE_EXTENSIONS:
            return "image"
        return "txt"
    value = str(source).strip()
    if is_youtube_url(value):
        return "youtube"
    return "text"


def _extract_pdf(data: bytes) -> tuple[str, str]:
    """Try text extraction first; fall back to OCR if page has no embedded text."""
    text = ""
    try:
        import PyPDF2  # type: ignore
        reader = PyPDF2.PdfReader(BytesIO(data))
        parts = []
        for page in reader.pages:
            try:
                parts.append((page.extract_text() or "").strip())
            except Exception:
                continue
        text = "\n\n".join(p for p in parts if p).strip()
    except Exception:
        pass

    if text and len(text.strip()) >= 50:
        return text, "text"

    # OCR fallback — scanned or image-only PDF
    try:
        from pdf2image import convert_from_bytes  # type: ignore
        import pytesseract  # type: ignore

        images = convert_from_bytes(data, dpi=200)
        ocr_parts = []
        for image in images:
            try:
                page_text = pytesseract.image_to_string(image).strip()
                if page_text:
                    ocr_parts.append(page_text)
            except Exception:
                continue
        ocr_text = "\n\n".join(ocr_parts).strip()
        if ocr_text:
            return ocr_text, "ocr"
    except Exception:
        pass

    if text:
        return text, "text"

    raise RuntimeError(
        "No text could be extracted from this PDF. "
        "The file may be a scanned image without OCR support available."
    )


def _extract_docx(data: bytes) -> str:
    """Extract structured text from DOCX preserving headings and list items."""
    # Primary: python-docx for structured paragraph-level extraction
    try:
        import docx  # type: ignore

        document = docx.Document(BytesIO(data))
        parts = []
        for para in document.paragraphs:
            text = para.text.strip()
            if not text:
                continue
            style_name = (para.style.name if para.style else "").lower()
            if "heading" in style_name:
                parts.append(f"\n{text}\n")
            elif "list" in style_name:
                parts.append(f"- {text}")
            else:
                parts.append(text)
        result = "\n".join(parts).strip()
        if result:
            return result
    except Exception:
        pass

    # Fallback: zipfile + XML regex
    try:
        with zipfile.ZipFile(BytesIO(data)) as archive:
            with archive.open("word/document.xml") as xml_file:
                xml_content = xml_file.read().decode("utf-8", errors="replace")
        raw_parts = re.findall(r"<w:t[^>]*>([^<]*)</w:t>", xml_content)
        result = re.sub(r"\s+", " ", " ".join(raw_parts)).strip()
        if result:
            return result
    except Exception:
        pass

    raise RuntimeError("DOCX extraction failed with all available methods.")


def _extract_image(data: bytes) -> str:
    """Extract text from an image via Tesseract OCR."""
    try:
        import pytesseract  # type: ignore
        from PIL import Image  # type: ignore

        image = Image.open(BytesIO(data))
        text = pytesseract.image_to_string(image).strip()
        if text:
            return text
        raise RuntimeError("OCR returned no text from this image.")
    except ImportError:
        raise RuntimeError(
            "pytesseract and Pillow are required for image OCR. "
            "Tesseract must also be installed as a system tool."
        )
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(f"Image OCR failed: {exc}") from exc


def _extract_youtube(url: str) -> tuple[str, str]:
    """Fetch full transcript if available; fall back to metadata summary."""
    video_id = _extract_video_id(url)

    # Primary: real transcript via youtube-transcript-api
    if video_id:
        try:
            from youtube_transcript_api import YouTubeTranscriptApi  # type: ignore

            api = YouTubeTranscriptApi()
            fetched = api.fetch(video_id)
            full_text = " ".join(
                str(getattr(snippet, "text", "")).strip()
                for snippet in fetched
                if str(getattr(snippet, "text", "")).strip()
            ).strip()
            if full_text and len(full_text) >= 100:
                return full_text, "transcript"
        except Exception:
            pass

    # Fallback: metadata-based summary from existing youtube_agent
    try:
        from agents.integration.youtube_agent import summarize_youtube  # deferred import

        result = summarize_youtube(url)
        if result.get("success"):
            metadata_text = str(result.get("message") or "").strip()
            if metadata_text:
                labeled = (
                    "[Note: Full transcript unavailable — summary derived from video metadata only.]\n\n"
                    + metadata_text
                )
                return labeled, "metadata"
    except Exception:
        pass

    raise RuntimeError(
        "YouTube extraction failed: transcript unavailable and metadata fetch failed."
    )


def extract_content(
    source: Union[str, Path, bytes],
    *,
    source_type: Optional[str] = None,
    filename: Optional[str] = None,
) -> ExtractedContent:
    """Normalize any supported source into plain text.

    source: raw text string, file Path, bytes from an upload, or a YouTube URL.
    source_type: override detection — "text", "txt", "pdf", "docx", "image", "youtube".
    filename: used when source is bytes to detect type from file extension.
    """
    detected = source_type or _detect_type(source, filename)

    if isinstance(source, bytes):
        label: str = filename or "uploaded file"
    elif isinstance(source, Path):
        label = source.name
    else:
        label = str(source)[:80]

    try:
        if detected == "text":
            text = str(source).strip()
            return ExtractedContent(
                text=text,
                source_type="text",
                source_label="pasted text",
                success=bool(text),
                error=None if text else "Empty text provided.",
                extraction_mode="text",
            )

        if detected == "txt":
            path = Path(source)  # type: ignore[arg-type]
            text = path.read_text(encoding="utf-8", errors="replace").strip()
            return ExtractedContent(
                text=text,
                source_type="txt",
                source_label=path.name,
                success=bool(text),
                error=None if text else "File is empty.",
                extraction_mode="text",
            )

        if detected == "txt_bytes":
            text = bytes(source).decode("utf-8", errors="replace").strip()  # type: ignore[arg-type]
            return ExtractedContent(
                text=text,
                source_type="txt",
                source_label=label,
                success=bool(text),
                error=None if text else "File is empty.",
                extraction_mode="text",
            )

        if detected in {"pdf", "pdf_bytes"}:
            data = bytes(source) if isinstance(source, bytes) else Path(source).read_bytes()  # type: ignore[arg-type]
            text, mode = _extract_pdf(data)
            return ExtractedContent(
                text=text,
                source_type="pdf",
                source_label=label,
                success=bool(text),
                error=None if text else "No text could be extracted from this PDF.",
                extraction_mode=mode,
            )

        if detected in {"docx", "docx_bytes"}:
            data = bytes(source) if isinstance(source, bytes) else Path(source).read_bytes()  # type: ignore[arg-type]
            text = _extract_docx(data)
            return ExtractedContent(
                text=text,
                source_type="docx",
                source_label=label,
                success=bool(text),
                error=None if text else "No text could be extracted from this DOCX.",
                extraction_mode="structured",
            )

        if detected in {"image", "image_bytes"}:
            data = bytes(source) if isinstance(source, bytes) else Path(source).read_bytes()  # type: ignore[arg-type]
            text = _extract_image(data)
            return ExtractedContent(
                text=text,
                source_type="image",
                source_label=label,
                success=bool(text),
                error=None if text else "No text could be extracted from this image.",
                extraction_mode="ocr",
            )

        if detected == "youtube":
            text, mode = _extract_youtube(str(source))
            return ExtractedContent(
                text=text,
                source_type="youtube",
                source_label=str(source),
                success=bool(text),
                error=None if text else "No content could be extracted from this YouTube URL.",
                extraction_mode=mode,
            )

        return ExtractedContent(
            text="",
            source_type=detected,
            source_label=label,
            success=False,
            error=f"Unsupported source type: {detected}",
        )

    except Exception as exc:
        return ExtractedContent(
            text="",
            source_type=detected,
            source_label=label,
            success=False,
            error=str(exc),
        )
