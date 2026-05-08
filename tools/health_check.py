from __future__ import annotations

"""Small read-only health check for the supported local AURA runtime."""

import json
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_BASE_URL = "http://127.0.0.1:5000"
ENDPOINTS = (
    "/api/auth/session",
    "/api/assistant/runtime",
    "/api/desktop/apps",
    "/api/system/health",
)


def _fetch_json(url: str, timeout: float = 5.0) -> tuple[bool, dict[str, Any]]:
    request = Request(url, headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=timeout) as response:
            status_code = int(getattr(response, "status", 0) or 0)
            body = response.read().decode("utf-8", errors="replace")
    except HTTPError as error:
        return False, {"status_code": error.code, "error": str(error)}
    except URLError as error:
        return False, {"error": str(error.reason)}
    except Exception as error:
        return False, {"error": str(error)}

    try:
        payload: Any = json.loads(body)
    except json.JSONDecodeError:
        payload = {"raw": body[:200]}
    return 200 <= status_code < 400, {"status_code": status_code, "payload": payload}


def run_health_check(base_url: str = DEFAULT_BASE_URL) -> dict[str, Any]:
    normalized_base = str(base_url or DEFAULT_BASE_URL).rstrip("/")
    results: dict[str, Any] = {}
    overall_ok = True

    for endpoint in ENDPOINTS:
        ok, payload = _fetch_json(f"{normalized_base}{endpoint}")
        results[endpoint] = {"ok": ok, **payload}
        overall_ok = overall_ok and ok

    return {
        "success": overall_ok,
        "base_url": normalized_base,
        "checks": results,
    }


def main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    base_url = args[0] if args else DEFAULT_BASE_URL
    report = run_health_check(base_url)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
