from __future__ import annotations

import json
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from typing import Dict

from security.security_config import SESSION_APPROVAL_DELTA


SESSION_FILE = Path("memory/session_approvals.json")


def _load_sessions() -> Dict[str, Dict[str, str]]:
    if not SESSION_FILE.exists():
        return {}
    try:
        payload = json.loads(SESSION_FILE.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _save_sessions(payload: Dict[str, Dict[str, str]]) -> None:
    SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
    SESSION_FILE.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def approve_action(session_id: str, action_name: str, *, minutes: int | None = None) -> Dict[str, object]:
    ttl = SESSION_APPROVAL_DELTA if minutes is None else timedelta(minutes=minutes)
    payload = _load_sessions()
    session_key = str(session_id or "default").strip()
    payload.setdefault(session_key, {})
    payload[session_key][str(action_name or "").strip().lower()] = (datetime.now() + ttl).isoformat()
    _save_sessions(payload)
    return {"success": True, "session_id": session_key, "action_name": action_name}


def is_action_approved(session_id: str, action_name: str) -> bool:
    payload = _load_sessions()
    session_key = str(session_id or "default").strip()
    expiry = payload.get(session_key, {}).get(str(action_name or "").strip().lower())
    if not expiry:
        return False
    try:
        if datetime.now() <= datetime.fromisoformat(expiry):
            return True
    except Exception:
        pass
    revoke_action(session_id, action_name)
    return False


def revoke_action(session_id: str, action_name: str) -> None:
    payload = _load_sessions()
    session_key = str(session_id or "default").strip()
    if session_key in payload:
        payload[session_key].pop(str(action_name or "").strip().lower(), None)
        _save_sessions(payload)
