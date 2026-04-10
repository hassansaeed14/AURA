from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from config.memory_config import MAX_SEMANTIC_FACTS


SEMANTIC_MEMORY_FILE = Path("memory/semantic_memory.json")


@dataclass(slots=True)
class SemanticFact:
    key: str
    value: str
    confidence: float
    source: str
    updated_at: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


def _read_facts() -> Dict[str, Dict[str, object]]:
    if not SEMANTIC_MEMORY_FILE.exists():
        return {}
    try:
        payload = json.loads(SEMANTIC_MEMORY_FILE.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _write_facts(payload: Dict[str, Dict[str, object]]) -> None:
    items = list(payload.items())[-MAX_SEMANTIC_FACTS:]
    normalized = {key: value for key, value in items}
    SEMANTIC_MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    SEMANTIC_MEMORY_FILE.write_text(json.dumps(normalized, indent=2, ensure_ascii=False), encoding="utf-8")


def remember_fact(key: str, value: str, *, confidence: float = 1.0, source: str = "semantic_memory") -> SemanticFact:
    normalized_key = str(key or "").strip().lower().replace(" ", "_")
    fact = SemanticFact(
        key=normalized_key,
        value=str(value or "").strip(),
        confidence=max(0.0, min(1.0, float(confidence))),
        source=source,
        updated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )
    payload = _read_facts()
    payload[normalized_key] = fact.to_dict()
    _write_facts(payload)
    return fact


def recall_fact(key: str) -> Optional[Dict[str, object]]:
    return _read_facts().get(str(key or "").strip().lower().replace(" ", "_"))


def list_facts() -> List[Dict[str, object]]:
    return list(_read_facts().values())
