from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Dict, List

from brain.entity_parser import parse_entities
from config.memory_config import LOW_VALUE_INTENTS, REUSABLE_CONTEXT_CONFIDENCE, STABLE_MEMORY_CONFIDENCE


@dataclass(slots=True)
class MemoryCandidate:
    destination: str
    key: str
    value: str
    confidence: float
    reason: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


def extract_memory_candidates(user_input: str, response: str, intent: str, confidence: float) -> List[MemoryCandidate]:
    lowered = str(user_input or "").lower().strip()
    if not lowered or intent in LOW_VALUE_INTENTS or confidence < REUSABLE_CONTEXT_CONFIDENCE:
        return []

    entities = parse_entities(user_input)
    candidates: List[MemoryCandidate] = []

    name_match = re.search(r"\b(?:my name is|call me)\s+([a-zA-Z][a-zA-Z .'-]{0,39})", user_input, flags=re.IGNORECASE)
    if name_match and confidence >= STABLE_MEMORY_CONFIDENCE:
        name = re.split(r"\b(?:and|but|then)\b|[,.!?]", name_match.group(1).strip(), maxsplit=1, flags=re.IGNORECASE)[0]
        if name.strip():
            candidates.append(MemoryCandidate("semantic", "user_name", name.strip().title(), confidence, "explicit_name"))

    city_match = re.search(r"\b(?:i live in|my city is)\s+([a-zA-Z ]{2,40})", lowered)
    if city_match and confidence >= STABLE_MEMORY_CONFIDENCE:
        candidates.append(MemoryCandidate("semantic", "user_city", city_match.group(1).strip().title(), confidence, "explicit_city"))

    if "prefer" in lowered or "default" in lowered or "usually" in lowered:
        candidates.append(MemoryCandidate("semantic", "user_preference", user_input.strip(), confidence, "explicit_preference"))

    if entities.files:
        candidates.append(MemoryCandidate("working", "active_file", entities.files[0], confidence, "recent_file_context"))
    if entities.urls:
        candidates.append(MemoryCandidate("working", "active_url", entities.urls[0], confidence, "recent_url_context"))
    if entities.primary_topic:
        candidates.append(MemoryCandidate("working", "active_topic", entities.primary_topic, confidence, "recent_topic_context"))

    if intent in {"task", "reminder", "file", "translation", "research"}:
        candidates.append(MemoryCandidate("episodic", "last_action", f"{intent}: {user_input.strip()}", confidence, "useful_event"))

    return candidates
