from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict

from security.encryption_utils import hash_secret, verify_secret
from security.security_config import PIN_LOCKOUT_DELTA, PIN_RETRY_LIMIT


PIN_STATE_FILE = Path("memory/pin_state.json")


def _default_state() -> Dict[str, object]:
    return {
        "pin_hash": None,
        "failed_attempts": 0,
        "locked_until": None,
        "updated_at": None,
    }


def _load_state() -> Dict[str, object]:
    if not PIN_STATE_FILE.exists():
        return _default_state()
    try:
        payload = json.loads(PIN_STATE_FILE.read_text(encoding="utf-8"))
        return {**_default_state(), **payload}
    except Exception:
        return _default_state()


def _save_state(payload: Dict[str, object]) -> None:
    PIN_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    PIN_STATE_FILE.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def has_pin() -> bool:
    return bool(_load_state().get("pin_hash"))


def set_pin(pin: str) -> Dict[str, object]:
    normalized = str(pin or "").strip()
    if not normalized.isdigit() or len(normalized) < 4:
        return {"success": False, "reason": "PIN must be at least 4 digits."}

    payload = _default_state()
    payload["pin_hash"] = hash_secret(normalized)
    _save_state(payload)
    return {"success": True, "reason": "PIN saved."}


def verify_pin(pin: str) -> Dict[str, object]:
    payload = _load_state()
    if not payload.get("pin_hash"):
        return {"success": False, "reason": "PIN is not configured.", "status": "not_configured"}

    locked_until = payload.get("locked_until")
    if locked_until:
        try:
            if datetime.now() < datetime.fromisoformat(str(locked_until)):
                return {"success": False, "reason": "PIN entry is temporarily locked.", "status": "locked"}
        except Exception:
            payload["locked_until"] = None

    if verify_secret(str(pin or "").strip(), str(payload["pin_hash"])):
        payload["failed_attempts"] = 0
        payload["locked_until"] = None
        _save_state(payload)
        return {"success": True, "reason": "PIN verified.", "status": "verified"}

    payload["failed_attempts"] = int(payload.get("failed_attempts", 0)) + 1
    if payload["failed_attempts"] >= PIN_RETRY_LIMIT:
        payload["locked_until"] = (datetime.now() + PIN_LOCKOUT_DELTA).isoformat()
    _save_state(payload)
    return {"success": False, "reason": "Incorrect PIN.", "status": "denied", "failed_attempts": payload["failed_attempts"]}


def get_pin_status() -> Dict[str, object]:
    payload = _load_state()
    return {
        "configured": bool(payload.get("pin_hash")),
        "failed_attempts": int(payload.get("failed_attempts", 0)),
        "locked_until": payload.get("locked_until"),
    }
