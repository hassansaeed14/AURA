from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from config.memory_config import MAX_WORKING_MEMORY_ITEMS


WORKING_MEMORY_FILE = Path("memory/working_memory.json")


@dataclass(slots=True)
class WorkingMemoryState:
    active_topic: Optional[str] = None
    active_file: Optional[str] = None
    active_url: Optional[str] = None
    last_agent: Optional[str] = None
    last_task: Optional[str] = None
    last_translation: Optional[str] = None
    current_goal: Optional[str] = None
    current_mode: str = "smart"
    unresolved_follow_up: Optional[str] = None
    recent_references: List[str] = field(default_factory=list)
    updated_at: str = ""

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


def _read_store() -> Dict[str, Dict[str, object]]:
    if not WORKING_MEMORY_FILE.exists():
        return {}
    try:
        return json.loads(WORKING_MEMORY_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_store(payload: Dict[str, Dict[str, object]]) -> None:
    WORKING_MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    WORKING_MEMORY_FILE.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def load_working_memory(session_id: str = "default") -> WorkingMemoryState:
    payload = _read_store().get(session_id, {})
    try:
        return WorkingMemoryState(**payload)
    except Exception:
        return WorkingMemoryState()


def save_working_memory(state: WorkingMemoryState, session_id: str = "default") -> None:
    payload = _read_store()
    state.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    payload[session_id] = state.to_dict()
    _write_store(payload)


def update_working_memory(session_id: str = "default", **updates: object) -> WorkingMemoryState:
    state = load_working_memory(session_id)
    for key, value in updates.items():
        if value is None or not hasattr(state, key):
            continue
        setattr(state, key, value)

    if "recent_references" in updates:
        refs = [str(item).strip() for item in list(updates["recent_references"]) if str(item).strip()]
        state.recent_references = refs[-MAX_WORKING_MEMORY_ITEMS:]
    save_working_memory(state, session_id)
    return state


def remember_reference(reference: str, session_id: str = "default") -> WorkingMemoryState:
    state = load_working_memory(session_id)
    ref = str(reference or "").strip()
    if not ref:
        return state
    refs = [item for item in state.recent_references if item.lower() != ref.lower()]
    refs.append(ref)
    state.recent_references = refs[-MAX_WORKING_MEMORY_ITEMS:]
    save_working_memory(state, session_id)
    return state


def clear_working_memory(session_id: str = "default") -> None:
    payload = _read_store()
    if session_id in payload:
        payload.pop(session_id, None)
        _write_store(payload)
