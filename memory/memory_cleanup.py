from __future__ import annotations

from typing import Dict, List

from memory.episodic_memory import list_events
from memory.semantic_memory import list_facts


def deduplicate_semantic_facts() -> List[Dict[str, object]]:
    seen = set()
    cleaned = []
    for fact in list_facts():
        signature = (fact.get("key"), fact.get("value"))
        if signature in seen:
            continue
        seen.add(signature)
        cleaned.append(fact)
    return cleaned


def deduplicate_episodic_events() -> List[Dict[str, object]]:
    seen = set()
    cleaned = []
    for event in list_events(limit=500):
        signature = (event.get("event_type"), event.get("summary"))
        if signature in seen:
            continue
        seen.add(signature)
        cleaned.append(event)
    return cleaned
