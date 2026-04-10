from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict


AUDIT_LOG_FILE = Path("memory/security_audit.jsonl")


def record_audit_event(*, action_name: str, allowed: bool, trust_level: str, reason: str, username: str | None = None, session_id: str | None = None) -> Dict[str, object]:
    event = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "action_name": action_name,
        "allowed": allowed,
        "trust_level": trust_level,
        "reason": reason,
        "username": username,
        "session_id": session_id,
    }
    AUDIT_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT_LOG_FILE.open("a", encoding="utf-8") as file:
        file.write(json.dumps(event, ensure_ascii=False) + "\n")
    return event
