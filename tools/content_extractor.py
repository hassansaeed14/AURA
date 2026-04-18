"""
Content extraction for AURA's transformation engine.
Normalizes: raw text, .txt, .pdf, .docx (path or bytes), YouTube URLs.
"""
from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Optional, Union


@dataclass(slots=True)
class ExtractedContent:
    text: str
    source_type: str
    source_label: str
    success: bool
    error: Optional[str] = None


_YOUTUBE_URL_RE = re.compile(
    r"(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?v=[\w-]+|youtu\.be/[\w-]+|youtube\.com/shorts/[\w-]+)",
    flags=re.IGNORECASE,
)


def is_youtube_url(value: str) -> bool:
    return bool(_YOUTUBE_URL_RE.search(str(value or "")))


def _detect_type(source: Union[str, Path, bytes], filename: Optional[str]) -> str:
    if isinstance(source, bytes):
        if filename:
            ext = Path(filename).suffix.lower()
            if ext == ".pdf":
                return "pdf_bytes"
            if ext == ".docx":
                return "docx_bytes"
        return "txt_bytes"
    if isinstance(source, Path):
        ext = source.suffix.lower()
        if ext == ".pdf":
            return "pdf"
        if ext == ".docx":
            return "docx"
        return "txt"
    value = str(source).strip()
    if is_youtube_url(value):
        return "youtube"
    return "text"


def _extract_pdf(data: bytes) -> str:
    try:
        import PyPDF2  # type: ignore
        reader = PyPDF2.PdfReader(BytesIO(data))
        parts = []
        for page in reader.pages:
            try:
                parts.append((page.extract_text() or "").strip())
            except Exception:
                continue
        return "\n\n".join(p for p in parts if p).strip()
    except Exception as exc:
        raise RuntimeError(f"PDF extraction failed: {exc}") from exc


def _extract_docx(data: bytes) -> str:
    try:
        with zipfile.ZipFile(BytesIO(data)) as archive:
            with archive.open("word/document.xml") as xml_file:
                xml_content = xml_file.read().decode("utf-8", errors="replace")
        parts = re.findall(r"<w:t[^>]*>([^<]*)</w:t>", xml_content)
        return re.sub(r"\s+", " ", " ".join(parts)).strip()
    except Exception as exc:
        raise RuntimeError(f"DOCX extraction failed: {exc}") from exc


def _extract_youtube(url: str) -> str:
    from agents.integration.youtube_agent import summarize_youtube  # deferred — youtube_agent imports Groq at module level
    result = summarize_youtube(url)
    if result.get("success"):
        return str(result.get("message") or "").strip()
    raise RuntimeError(result.get("error") or "YouTube extraction failed.")


def extract_content(
    source: Union[str, Path, bytes],
    *,
    source_type: Optional[str] = None,
    filename: Optional[str] = None,
) -> ExtractedContent:
    """Normalize any supported source into plain text.

    source: raw text string, file Path, bytes from an upload, or a YouTube URL.
    source_type: override detection — "text", "txt", "pdf", "docx", "youtube".
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
            )

        if detected == "txt_bytes":
            text = bytes(source).decode("utf-8", errors="replace").strip()  # type: ignore[arg-type]
            return ExtractedContent(
                text=text,
                source_type="txt",
                source_label=label,
                success=bool(text),
                error=None if text else "File is empty.",
            )

        if detected in {"pdf", "pdf_bytes"}:
            data = bytes(source) if isinstance(source, bytes) else Path(source).read_bytes()  # type: ignore[arg-type]
            text = _extract_pdf(data)
            return ExtractedContent(
                text=text,
                source_type="pdf",
                source_label=label,
                success=bool(text),
                error=None if text else "No text could be extracted from this PDF.",
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
            )

        if detected == "youtube":
            text = _extract_youtube(str(source))
            return ExtractedContent(
                text=text,
                source_type="youtube",
                source_label=str(source),
                success=bool(text),
                error=None if text else "No content could be extracted from this YouTube URL.",
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
