from __future__ import annotations

from typing import Dict, List

from memory.episodic_memory import list_events
from memory.semantic_memory import list_facts
from memory.working_memory import load_working_memory


def search_memory(query: str, *, session_id: str = "default", limit: int = 10) -> List[Dict[str, object]]:
    needle = str(query or "").strip().lower()
    if not needle:
        return []

    results: List[Dict[str, object]] = []

    for fact in list_facts():
        haystack = " ".join(str(fact.get(key, "")) for key in ("key", "value", "source")).lower()
        if needle in haystack:
            results.append({"memory_type": "semantic", "item": fact})

    for event in list_events(limit=100):
        haystack = " ".join(str(event.get(key, "")) for key in ("event_type", "summary", "intent")).lower()
        if needle in haystack:
            results.append({"memory_type": "episodic", "item": event})

    working = load_working_memory(session_id).to_dict()
    haystack = " ".join(str(value) for value in working.values()).lower()
    if needle in haystack:
        results.append({"memory_type": "working", "item": working})

    return results[:limit]
