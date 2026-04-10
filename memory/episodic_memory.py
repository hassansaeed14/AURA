from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from config.memory_config import MAX_EPISODIC_EVENTS


EPISODIC_MEMORY_FILE = Path("memory/episodic_memory.json")


@dataclass(slots=True)
class EpisodicEvent:
    event_type: str
    summary: str
    timestamp: str
    intent: Optional[str] = None
    success: Optional[bool] = None
    metadata: Dict[str, object] | None = None

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


def _read_events() -> List[Dict[str, object]]:
    if not EPISODIC_MEMORY_FILE.exists():
        return []
    try:
        return json.loads(EPISODIC_MEMORY_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _write_events(events: List[Dict[str, object]]) -> None:
    EPISODIC_MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    EPISODIC_MEMORY_FILE.write_text(json.dumps(events[-MAX_EPISODIC_EVENTS:], indent=2, ensure_ascii=False), encoding="utf-8")


def record_event(event_type: str, summary: str, *, intent: str | None = None, success: bool | None = None, metadata: Dict[str, object] | None = None) -> EpisodicEvent:
    event = EpisodicEvent(
        event_type=event_type,
        summary=str(summary or "").strip(),
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        intent=intent,
        success=success,
        metadata=metadata or {},
    )
    payload = _read_events()
    payload.append(event.to_dict())
    _write_events(payload)
    return event


def list_events(limit: int = 20) -> List[Dict[str, object]]:
    return _read_events()[-limit:]
