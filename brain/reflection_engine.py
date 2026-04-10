from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List


IMPROVEMENT_LOG_FILE = Path("memory/aura_improvement_log.json")


def _load_log() -> Dict[str, object]:
    if not IMPROVEMENT_LOG_FILE.exists():
        return {
            "failures": [],
            "low_confidence_commands": [],
            "agent_errors": [],
            "user_corrections": [],
            "improvement_suggestions": [],
            "reflections": [],
            "last_reviewed": None,
        }
    try:
        payload = json.loads(IMPROVEMENT_LOG_FILE.read_text(encoding="utf-8"))
        payload.setdefault("reflections", [])
        return payload
    except Exception:
        return {
            "failures": [],
            "low_confidence_commands": [],
            "agent_errors": [],
            "user_corrections": [],
            "improvement_suggestions": [],
            "reflections": [],
            "last_reviewed": None,
        }


def _save_log(payload: Dict[str, object]) -> None:
    IMPROVEMENT_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    IMPROVEMENT_LOG_FILE.write_text(json.dumps(payload, indent=4, ensure_ascii=False), encoding="utf-8")


def record_reflection(*, requested_action: str, actual_action: str, success: bool, blocked_by_permission: bool, retry_possible: bool, learning_signal: str) -> Dict[str, object]:
    payload = _load_log()
    reflection = {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "requested_action": requested_action,
        "actual_action": actual_action,
        "success": success,
        "blocked_by_permission": blocked_by_permission,
        "retry_possible": retry_possible,
        "learning_signal": learning_signal,
    }
    payload["reflections"].append(reflection)
    _save_log(payload)
    return reflection


def list_recent_reflections(limit: int = 10) -> List[Dict[str, object]]:
    return list(_load_log().get("reflections", []))[-limit:]
