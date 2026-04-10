from __future__ import annotations

from typing import Dict, List

from brain.memory_extractor import MemoryCandidate, extract_memory_candidates
from memory.episodic_memory import record_event
from memory.semantic_memory import remember_fact
from memory.working_memory import update_working_memory

try:
    from memory.vector_memory import store_memory
except Exception:
    def store_memory(*args, **kwargs):
        return None


def route_memory_candidate(candidate: MemoryCandidate, *, session_id: str = "default") -> Dict[str, object]:
    if candidate.destination == "semantic":
        fact = remember_fact(candidate.key, candidate.value, confidence=candidate.confidence, source="memory_controller")
        return {"destination": "semantic", "stored": fact.to_dict()}

    if candidate.destination == "working":
        state = update_working_memory(session_id, **{candidate.key: candidate.value})
        return {"destination": "working", "stored": state.to_dict()}

    if candidate.destination == "episodic":
        event = record_event("memory_signal", candidate.value, intent=candidate.key, success=True, metadata={"reason": candidate.reason})
        return {"destination": "episodic", "stored": event.to_dict()}

    store_memory(candidate.value, {"type": candidate.key, "reason": candidate.reason, "confidence": candidate.confidence})
    return {"destination": "vector", "stored": {"value": candidate.value}}


def process_interaction_memory(user_input: str, response: str, intent: str, confidence: float, *, session_id: str = "default") -> List[Dict[str, object]]:
    candidates = extract_memory_candidates(user_input, response, intent, confidence)
    return [route_memory_candidate(candidate, session_id=session_id) for candidate in candidates]
