from __future__ import annotations

import re
import subprocess
from typing import Any, Dict, Optional
from urllib.parse import urlencode, urlparse, urlunparse

from tools.desktop_controller import get_application_availability


MAX_BROWSER_TARGET_LENGTH = 220
MAX_RESULT_INDEX = 3


def _clean_text(value: str | None, *, limit: int = MAX_BROWSER_TARGET_LENGTH) -> str:
    return " ".join(str(value or "").replace("\x00", " ").split())[:limit].strip()


def normalize_browser_url(target: str | None) -> Optional[str]:
    text = _clean_text(target)
    if not text:
        return None
    if "://" not in text:
        scheme_like = re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", text)
        domain_port = re.match(r"^[A-Za-z0-9.-]+\.[A-Za-z]{2,}:\d", text)
        localhost_port = re.match(r"^localhost:\d", text, re.IGNORECASE)
        if scheme_like and not (domain_port or localhost_port):
            return None
    if "://" not in text:
        text = f"https://{text}"

    parsed = urlparse(text)
    if parsed.scheme not in {"http", "https"}:
        return None
    if not parsed.netloc or any(char.isspace() for char in parsed.netloc):
        return None
    if parsed.username or parsed.password:
        return None

    return urlunparse(parsed)


def _bounded_result_index(result_index: int | str | None) -> int:
    try:
        parsed = int(result_index or 1)
    except (TypeError, ValueError):
        parsed = 1
    return max(1, min(parsed, MAX_RESULT_INDEX))


def _google_search_url(query: str, *, top_result: bool = False, result_index: int = 1) -> str:
    safe_index = _bounded_result_index(result_index)
    params = {"q": query}
    if safe_index > 1:
        params["start"] = str(safe_index - 1)
    if top_result:
        # Google handles the result redirect; AURA does not scrape or inspect the page.
        params["btnI"] = "I"
    return "https://www.google.com/search?" + urlencode(params)


def _chrome_unavailable_payload(url: str | None = None) -> Dict[str, Any]:
    payload = {
        "success": False,
        "verified": False,
        "status": "unavailable",
        "app_name": "chrome",
        "label": "Chrome",
        "message": "I couldn't find Chrome on this system.",
        "error": "Chrome is not installed or not discoverable from the safe allowlist.",
    }
    if url:
        payload["url"] = url
    return payload


def _launch_chrome_args(
    args: list[str],
    *,
    status: str,
    message: str,
    verification_url: str | None = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    availability = get_application_availability("chrome")
    launch_command = availability.get("launch_command")
    if not availability.get("available") or not launch_command:
        return _chrome_unavailable_payload(verification_url)

    try:
        process = subprocess.Popen(list(launch_command) + list(args), shell=False)
        pid = getattr(process, "pid", None)
        result = {
            "success": True,
            "verified": bool(pid and (not verification_url or verification_url.startswith(("http://", "https://")))),
            "verification": "Chrome accepted a validated browser launch request.",
            "status": status,
            "app_name": "chrome",
            "label": "Chrome",
            "launched_with": launch_command[0],
            "pid": pid,
            "message": message,
        }
        if verification_url:
            result["url"] = verification_url
        if extra:
            result.update(extra)
        return result
    except FileNotFoundError:
        return _chrome_unavailable_payload(verification_url)
    except OSError as error:
        error_text = str(error).strip() or "The browser launch request failed."
        payload = {
            "success": False,
            "verified": False,
            "status": "launch_failed",
            "app_name": "chrome",
            "label": "Chrome",
            "message": f"I couldn't complete the browser action because Chrome launch failed: {error_text}",
            "error": error_text,
        }
        if verification_url:
            payload["url"] = verification_url
        return payload


def _launch_chrome_url(url: str, *, status: str, message: str, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    normalized_url = normalize_browser_url(url)
    if not normalized_url:
        return {
            "success": False,
            "verified": False,
            "status": "invalid_url",
            "message": "I can only open safe http or https browser URLs.",
            "error": "Invalid or unsupported browser URL.",
        }
    return _launch_chrome_args(
        [normalized_url],
        status=status,
        message=message,
        verification_url=normalized_url,
        extra=extra,
    )


def open_new_tab() -> Dict[str, Any]:
    return _launch_chrome_args(
        ["--new-tab"],
        status="new_tab_opened",
        message="Opening a new Chrome tab.",
        extra={"new_tab": True},
    )


def open_url(target: str | None) -> Dict[str, Any]:
    normalized_url = normalize_browser_url(target)
    if not normalized_url:
        return {
            "success": False,
            "verified": False,
            "status": "invalid_url",
            "message": "I can only open safe http or https browser URLs.",
            "error": "Invalid or unsupported browser URL.",
        }
    return _launch_chrome_url(
        normalized_url,
        status="opened_url",
        message=f"Opening {normalized_url}.",
    )


def navigate_to_url(target: str | None) -> Dict[str, Any]:
    normalized_url = normalize_browser_url(target)
    if not normalized_url:
        return {
            "success": False,
            "verified": False,
            "status": "invalid_url",
            "message": "I can only navigate to safe http or https browser URLs.",
            "error": "Invalid or unsupported browser URL.",
        }
    return _launch_chrome_url(
        normalized_url,
        status="navigated_url",
        message=f"Navigating to {normalized_url}.",
    )


def search_query(query: str | None) -> Dict[str, Any]:
    safe_query = _clean_text(query, limit=180)
    if not safe_query:
        return {
            "success": False,
            "verified": False,
            "status": "invalid_query",
            "message": "I need a search phrase before I can search in Chrome.",
            "error": "Missing search query.",
        }
    return _launch_chrome_url(
        _google_search_url(safe_query),
        status="searched",
        message=f"Searching for {safe_query}.",
        extra={"query": safe_query},
    )


def rerun_search(query: str | None) -> Dict[str, Any]:
    safe_query = _clean_text(query, limit=180)
    if not safe_query:
        return {
            "success": False,
            "verified": False,
            "status": "invalid_query",
            "message": "I need a search phrase before I can re-run a search.",
            "error": "Missing search query.",
        }
    return _launch_chrome_url(
        _google_search_url(safe_query),
        status="reran_search",
        message=f"Re-running the search for {safe_query}.",
        extra={"query": safe_query, "rerun": True},
    )


def open_search_result(query: str | None, *, result_index: int = 1) -> Dict[str, Any]:
    safe_query = _clean_text(query, limit=180)
    if not safe_query:
        return {
            "success": False,
            "verified": False,
            "status": "invalid_query",
            "message": "I need a search phrase before I can open the top result.",
            "error": "Missing search query for result action.",
        }
    safe_index = _bounded_result_index(result_index)
    ordinal = "top" if safe_index == 1 else "next"
    return _launch_chrome_url(
        _google_search_url(safe_query, top_result=True, result_index=safe_index),
        status="top_result_requested" if safe_index == 1 else "next_result_requested",
        message=f"Opening the {ordinal} result for {safe_query}.",
        extra={
            "query": safe_query,
            "top_result_only": safe_index == 1,
            "result_index": safe_index,
            "result_limit": MAX_RESULT_INDEX,
        },
    )
