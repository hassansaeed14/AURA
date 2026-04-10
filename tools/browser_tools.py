from __future__ import annotations

import webbrowser
from pathlib import Path
from typing import Dict
from urllib.parse import quote_plus

from tools.validation_tools import validate_url, validate_workspace_path


def looks_like_url(value: str) -> bool:
    text = str(value or "").strip()
    return validate_url(text) or text.startswith("localhost") or text.startswith("127.0.0.1")


def normalize_url(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError("URL is required.")
    if text.startswith("localhost") or text.startswith("127.0.0.1"):
        return f"http://{text}"
    if text.startswith("www."):
        return f"https://{text}"
    if text.startswith(("http://", "https://")):
        return text
    if validate_url(f"https://{text}"):
        return f"https://{text}"
    raise ValueError("Invalid URL.")


def open_url(value: str, *, launch: bool = False) -> Dict[str, object]:
    url = normalize_url(value)
    opened = webbrowser.open(url) if launch else False
    return {"url": url, "opened": bool(opened) if launch else False, "launch_mode": "real" if launch else "preview"}


def search_query(query: str, *, engine: str = "google", launch: bool = False) -> Dict[str, object]:
    text = str(query or "").strip()
    if not text:
        raise ValueError("Search query is required.")
    if engine.lower() == "duckduckgo":
        url = f"https://duckduckgo.com/?q={quote_plus(text)}"
    else:
        url = f"https://www.google.com/search?q={quote_plus(text)}"
    opened = webbrowser.open(url) if launch else False
    return {"query": text, "url": url, "opened": bool(opened) if launch else False, "launch_mode": "real" if launch else "preview"}


def open_local_page(path_value: str, *, launch: bool = False) -> Dict[str, object]:
    path = Path(path_value).expanduser().resolve()
    if not validate_workspace_path(path):
        raise ValueError("Local page must stay inside the workspace.")
    if not path.exists():
        raise FileNotFoundError(str(path))
    url = path.as_uri()
    opened = webbrowser.open(url) if launch else False
    return {"path": str(path), "url": url, "opened": bool(opened) if launch else False, "launch_mode": "real" if launch else "preview"}
