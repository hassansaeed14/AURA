from __future__ import annotations

from pathlib import Path
from typing import Dict

from memory.episodic_memory import list_events
from memory.memory_cleanup import deduplicate_episodic_events, deduplicate_semantic_facts
from memory.semantic_memory import list_facts
from memory.working_memory import load_working_memory


def get_memory_stats(session_id: str = "default") -> Dict[str, object]:
    semantic = list_facts()
    episodic = list_events(limit=500)
    working = load_working_memory(session_id).to_dict()

    return {
        "totals": {
            "working_keys": len([value for value in working.values() if value]),
            "semantic_facts": len(semantic),
            "episodic_events": len(episodic),
        },
        "deduplicated": {
            "semantic": len(deduplicate_semantic_facts()),
            "episodic": len(deduplicate_episodic_events()),
        },
        "recent_activity": episodic[-5:],
        "storage_size_bytes": sum(
            path.stat().st_size
            for path in (
                Path("memory/working_memory.json"),
                Path("memory/semantic_memory.json"),
                Path("memory/episodic_memory.json"),
            )
            if path.exists()
        ),
    }
