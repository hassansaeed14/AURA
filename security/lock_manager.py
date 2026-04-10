from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict

from security.security_config import LOCK_DEFAULT_DELTA


LOCKS_FILE = Path("memory/locks.json")


def _load_locks() -> Dict[str, Dict[str, str]]:
    if not LOCKS_FILE.exists():
        return {}
    try:
        payload = json.loads(LOCKS_FILE.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _save_locks(payload: Dict[str, Dict[str, str]]) -> None:
    LOCKS_FILE.parent.mkdir(parents=True, exist_ok=True)
    LOCKS_FILE.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def lock_resource(resource_id: str, *, owner: str | None = None) -> Dict[str, object]:
    payload = _load_locks()
    payload[str(resource_id)] = {
        "locked_until": (datetime.now() + LOCK_DEFAULT_DELTA).isoformat(),
        "owner": owner or "unknown",
    }
    _save_locks(payload)
    return {"success": True, "resource_id": resource_id}


def unlock_resource(resource_id: str) -> Dict[str, object]:
    payload = _load_locks()
    payload.pop(str(resource_id), None)
    _save_locks(payload)
    return {"success": True, "resource_id": resource_id}


def is_locked(resource_id: str) -> bool:
    payload = _load_locks()
    entry = payload.get(str(resource_id))
    if not entry:
        return False
    try:
        if datetime.now() <= datetime.fromisoformat(entry["locked_until"]):
            return True
    except Exception:
        pass
    payload.pop(str(resource_id), None)
    _save_locks(payload)
    return False
