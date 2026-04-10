from __future__ import annotations

from typing import Dict, Optional

from brain.entity_parser import parse_entities
from memory.working_memory import load_working_memory, remember_reference, update_working_memory


def get_context(session_id: str = "default") -> Dict[str, object]:
    return load_working_memory(session_id).to_dict()


def update_context_from_command(
    command: str,
    *,
    session_id: str = "default",
    agent: str | None = None,
    mode: str | None = None,
    unresolved_follow_up: str | None = None,
) -> Dict[str, object]:
    entities = parse_entities(command)
    updates = {
        "active_topic": entities.primary_topic,
        "active_file": entities.files[0] if entities.files else None,
        "active_url": entities.urls[0] if entities.urls else None,
        "last_agent": agent,
        "current_mode": mode,
        "unresolved_follow_up": unresolved_follow_up,
        "last_translation": entities.languages[0] if entities.languages else None,
    }
    state = update_working_memory(session_id, **updates)
    for reference in entities.files + entities.urls + entities.topics:
        remember_reference(reference, session_id)
    return state.to_dict()


def resolve_follow_up_reference(command: str, session_id: str = "default") -> Dict[str, Optional[str]]:
    lowered = str(command or "").lower()
    state = load_working_memory(session_id)
    if any(token in lowered for token in ("it", "that", "this", "same")):
        return {
            "topic": state.active_topic,
            "file": state.active_file,
            "url": state.active_url,
            "agent": state.last_agent,
        }
    return {"topic": None, "file": None, "url": None, "agent": None}
