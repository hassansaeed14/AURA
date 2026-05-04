from __future__ import annotations

import re
from typing import Dict, List, Optional

from brain.memory_extractor import MemoryCandidate, extract_memory_candidates
from memory.episodic_memory import record_event
from memory.semantic_memory import remember_fact
from memory.working_memory import update_working_memory

try:
    from memory.vector_memory import store_memory
except Exception:
    def store_memory(*args, **kwargs):
        return None


RESERVED_IDENTITY_VALUES = {"", "guest", "public", "anonymous", "unknown", "none", "null"}


def _normalize_scope(value: object) -> str:
    text = str(value or "").strip().lower()
    if not text or text in RESERVED_IDENTITY_VALUES:
        return ""
    return re.sub(r"[^a-z0-9_.:-]+", "_", text).strip("_")


def _scoped_semantic_key(scope_id: str, key: str) -> str:
    return f"user:{_normalize_scope(scope_id)}:{str(key or '').strip().lower()}"


def _memory_scope(*, user_id: Optional[str], username: Optional[str]) -> str:
    return _normalize_scope(user_id) or _normalize_scope(username)


def route_memory_candidate(
    candidate: MemoryCandidate,
    *,
    session_id: str = "default",
    user_id: Optional[str] = None,
    username: Optional[str] = None,
) -> Dict[str, object]:
    scope_id = _memory_scope(user_id=user_id, username=username)
    if not scope_id:
        return {
            "destination": candidate.destination,
            "stored": None,
            "skipped": True,
            "reason": "unscoped_public_memory_not_persisted",
        }

    if candidate.destination == "semantic":
        fact = remember_fact(
            _scoped_semantic_key(scope_id, candidate.key),
            candidate.value,
            confidence=candidate.confidence,
            source="memory_controller",
        )
        return {"destination": "semantic", "stored": fact.to_dict()}

    if candidate.destination == "working":
        state = update_working_memory(session_id, **{candidate.key: candidate.value})
        return {"destination": "working", "stored": state.to_dict()}

    if candidate.destination == "episodic":
        event = record_event(
            "memory_signal",
            candidate.value,
            intent=candidate.key,
            success=True,
            metadata={"reason": candidate.reason, "session_id": session_id, "user_id": user_id, "username": username},
        )
        return {"destination": "episodic", "stored": event.to_dict()}

    store_memory(
        candidate.value,
        {
            "type": candidate.key,
            "reason": candidate.reason,
            "confidence": candidate.confidence,
            "session_id": session_id,
            "user_id": user_id,
            "username": username,
        },
    )
    return {"destination": "vector", "stored": {"value": candidate.value}}


def process_interaction_memory(
    user_input: str,
    response: str,
    intent: str,
    confidence: float,
    *,
    session_id: str = "default",
    user_id: Optional[str] = None,
    username: Optional[str] = None,
) -> List[Dict[str, object]]:
    candidates = extract_memory_candidates(user_input, response, intent, confidence)
    return [
        route_memory_candidate(candidate, session_id=session_id, user_id=user_id, username=username)
        for candidate in candidates
    ]
