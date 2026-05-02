from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse


ACTION_MEMORY_FILE = Path("memory/action_memory.json")
MAX_EVENTS = 120


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _load_state() -> Dict[str, Any]:
    if not ACTION_MEMORY_FILE.exists():
        return {"events": [], "patterns": {}}
    try:
        payload = json.loads(ACTION_MEMORY_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"events": [], "patterns": {}}
    if not isinstance(payload, dict):
        return {"events": [], "patterns": {}}
    payload.setdefault("events", [])
    payload.setdefault("patterns", {})
    return payload


def _save_state(state: Dict[str, Any]) -> None:
    ACTION_MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    ACTION_MEMORY_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def _pattern_key(step: Dict[str, Any]) -> Optional[tuple[str, str, str]]:
    action_type = str(step.get("action_type") or "").strip()
    target = str(step.get("target") or "").strip()
    result = step.get("result") if isinstance(step.get("result"), dict) else {}
    query = str(result.get("query") or target).strip()
    url = str(result.get("url") or target).strip()

    if action_type in {"browser_search", "browser_rerun_search", "browser_open_result"} and query:
        return ("search", query.lower(), query)
    if action_type in {"browser_open_url", "browser_navigate_url"} and url:
        parsed = urlparse(url if "://" in url else f"https://{url}")
        host = parsed.netloc or parsed.path
        if host:
            return ("site", host.lower(), host)
    if action_type == "browser_new_tab":
        return ("browser", "new_tab", "new tab")
    return None


def record_action_plan(
    plan: Dict[str, Any] | None,
    *,
    session_id: str | None = None,
    username: str | None = None,
) -> Dict[str, Any]:
    if not isinstance(plan, dict):
        return {"recorded": False, "patterns": []}

    steps = [step for step in plan.get("steps", []) if isinstance(step, dict)]
    successful_steps = [step for step in steps if str(step.get("status") or "") == "success"]
    if not successful_steps:
        return {"recorded": False, "patterns": []}

    state = _load_state()
    events = state.get("events") if isinstance(state.get("events"), list) else []
    patterns = state.get("patterns") if isinstance(state.get("patterns"), dict) else {}
    touched: List[Dict[str, Any]] = []

    for step in successful_steps:
        pattern = _pattern_key(step)
        if not pattern:
            continue
        kind, key, label = pattern
        pattern_id = f"{kind}:{key}"
        record = patterns.get(pattern_id) if isinstance(patterns.get(pattern_id), dict) else {}
        count = int(record.get("count") or 0) + 1
        record.update(
            {
                "kind": kind,
                "key": key,
                "label": label,
                "count": count,
                "last_seen": _now(),
            }
        )
        patterns[pattern_id] = record
        touched.append(record.copy())

    if not touched:
        return {"recorded": False, "patterns": []}

    events.append(
        {
            "timestamp": _now(),
            "session_id": session_id,
            "username": username,
            "plan_id": plan.get("plan_id"),
            "original_command": plan.get("original_command"),
            "patterns": [{"kind": item["kind"], "label": item["label"]} for item in touched],
        }
    )
    state["events"] = events[-MAX_EVENTS:]
    state["patterns"] = patterns
    _save_state(state)
    return {"recorded": True, "patterns": touched}


def get_action_suggestions(plan: Dict[str, Any] | None = None, *, limit: int = 3) -> List[Dict[str, Any]]:
    state = _load_state()
    patterns = state.get("patterns") if isinstance(state.get("patterns"), dict) else {}
    seen_labels = {
        str(step.get("target") or "").strip().lower()
        for step in (plan or {}).get("steps", [])
        if isinstance(step, dict) and str(step.get("target") or "").strip()
    }

    suggestions: List[Dict[str, Any]] = []
    for record in patterns.values():
        if not isinstance(record, dict):
            continue
        count = int(record.get("count") or 0)
        label = str(record.get("label") or "").strip()
        kind = str(record.get("kind") or "").strip()
        if count < 2 or not label:
            continue
        if label.lower() in seen_labels:
            text = f"You often {('search ' if kind == 'search' else 'open ')}{label}."
        elif kind == "search":
            text = f"You often search {label}. Want me to use that again?"
        elif kind == "site":
            text = f"You often open {label}. Want me to go there again?"
        else:
            text = "You often open a new browser tab."
        suggestions.append(
            {
                "kind": kind,
                "label": label,
                "count": count,
                "text": text,
                "last_seen": record.get("last_seen"),
            }
        )

    suggestions.sort(key=lambda item: (int(item.get("count") or 0), str(item.get("last_seen") or "")), reverse=True)
    return suggestions[: max(0, int(limit or 0))]
