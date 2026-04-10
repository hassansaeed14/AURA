from __future__ import annotations

from typing import Dict, Tuple


MEMORY_CATEGORIES: Tuple[str, ...] = ("working", "episodic", "semantic", "vector")

MAX_WORKING_MEMORY_ITEMS = 24
MAX_EPISODIC_EVENTS = 500
MAX_SEMANTIC_FACTS = 250

MEMORY_STORE_LIMITS: Dict[str, int] = {
    "working": MAX_WORKING_MEMORY_ITEMS,
    "episodic": MAX_EPISODIC_EVENTS,
    "semantic": MAX_SEMANTIC_FACTS,
    "vector": 2000,
}

STABLE_MEMORY_CONFIDENCE = 0.72
REUSABLE_CONTEXT_CONFIDENCE = 0.5
VECTOR_MEMORY_CONFIDENCE = 0.68

LOW_VALUE_INTENTS: Tuple[str, ...] = ("greeting", "joke", "quote")
SENSITIVE_MEMORY_KEYS: Tuple[str, ...] = ("password", "payment", "pin", "secret", "token")


def get_memory_limits() -> Dict[str, int]:
    return dict(MEMORY_STORE_LIMITS)
