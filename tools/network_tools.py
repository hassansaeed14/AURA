from __future__ import annotations

from typing import Any, Dict, Iterable, Optional
from urllib.parse import urlparse

import requests


DEFAULT_TIMEOUT = 10
DEFAULT_RETRIES = 2


def _host_allowed(url: str, allowed_hosts: Optional[Iterable[str]]) -> bool:
    if not allowed_hosts:
        return True
    host = (urlparse(url).hostname or "").lower()
    return host in {str(item).strip().lower() for item in allowed_hosts}


def safe_request(
    method: str,
    url: str,
    *,
    timeout: int = DEFAULT_TIMEOUT,
    retries: int = DEFAULT_RETRIES,
    allowed_hosts: Optional[Iterable[str]] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    if not _host_allowed(url, allowed_hosts):
        return {"success": False, "status": "blocked_host", "message": "Host is not allowlisted.", "url": url}

    last_error = ""
    for attempt in range(retries + 1):
        try:
            response = requests.request(method.upper(), url, timeout=timeout, **kwargs)
            return {
                "success": response.ok,
                "status": response.status_code,
                "url": response.url,
                "headers": dict(response.headers),
                "text": response.text,
                "attempt": attempt + 1,
            }
        except requests.RequestException as error:
            last_error = str(error)

    return {"success": False, "status": "network_error", "message": last_error, "url": url}


def get_json(
    url: str,
    *,
    timeout: int = DEFAULT_TIMEOUT,
    retries: int = DEFAULT_RETRIES,
    allowed_hosts: Optional[Iterable[str]] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    result = safe_request("GET", url, timeout=timeout, retries=retries, allowed_hosts=allowed_hosts, **kwargs)
    if not result.get("success"):
        return result
    try:
        result["json"] = requests.models.complexjson.loads(result["text"])
    except Exception as error:
        result["success"] = False
        result["status"] = "json_decode_error"
        result["message"] = str(error)
    return result
