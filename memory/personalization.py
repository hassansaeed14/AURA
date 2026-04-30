from __future__ import annotations

import re
from collections import Counter
from typing import Any, Dict, Iterable, List, Optional

from agents.memory import learning_agent
from memory.knowledge_base import get_user_age, get_user_city, get_user_name
from memory.semantic_memory import list_facts, recall_fact, remember_fact
from memory.vector_memory import search_memory
from memory.working_memory import WorkingMemoryState, load_working_memory


MAX_CONTEXT_LINES = 9
MAX_RELEVANT_MEMORIES = 3


def _clean_text(value: Any, *, limit: int = 220) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) > limit:
        return text[: limit - 1].rstrip() + "..."
    return text


def _profile_value(profile: Dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = _clean_text(profile.get(key), limit=80)
        if value:
            return value
    return ""


def _display_name(value: str) -> str:
    text = _clean_text(value, limit=80)
    if not text:
        return ""
    return text.title() if text.islower() else text


def _semantic_value(key: str) -> str:
    fact = recall_fact(key) or {}
    return _clean_text(fact.get("value"), limit=120)


def get_personal_display_name(
    user_profile: Optional[Dict[str, Any]] = None,
    *,
    allow_memory_fallback: bool = True,
) -> str:
    profile = dict(user_profile or {})
    profile_name = _profile_value(profile, "preferred_name", "name", "username")
    if profile_name and profile_name.lower() not in {"guest", "public"}:
        return _display_name(profile_name)

    if allow_memory_fallback:
        semantic_name = _semantic_value("user_name")
        if semantic_name:
            return _display_name(semantic_name)

        stored_name = _clean_text(get_user_name(), limit=80)
        return _display_name(stored_name)

    return ""


def _load_learning_snapshot() -> Dict[str, Any]:
    try:
        data = learning_agent.load_data()
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _extract_learning_preferences(data: Dict[str, Any]) -> List[str]:
    profile = data.get("user_profile") if isinstance(data.get("user_profile"), dict) else {}
    preferences = profile.get("preferences") if isinstance(profile.get("preferences"), dict) else {}
    lines: List[str] = []
    for key, value in list(preferences.items())[:4]:
        key_text = _clean_text(key, limit=50)
        value_text = _clean_text(value, limit=90)
        if key_text and value_text:
            lines.append(f"{key_text}: {value_text}")

    for fact in list(data.get("learned_facts") or [])[-8:]:
        fact_text = _clean_text(fact, limit=140)
        if re.search(r"\b(?:prefer|usually|like|love|learning|study)\b", fact_text, re.IGNORECASE):
            lines.append(fact_text)
        if len(lines) >= 5:
            break
    return _dedupe(lines)[:5]


def _extract_semantic_preferences() -> List[str]:
    preferences: List[str] = []
    for fact in list_facts():
        key = str(fact.get("key") or "")
        value = _clean_text(fact.get("value"), limit=140)
        if value and ("preference" in key or "prefer" in value.lower() or "usually" in value.lower()):
            preferences.append(value)
    return _dedupe(preferences)[:5]


def _query_matches_memory_scope(
    memory: Dict[str, Any],
    *,
    session_id: str,
    user_profile: Dict[str, Any],
) -> bool:
    metadata = memory.get("metadata") if isinstance(memory.get("metadata"), dict) else {}
    memory_session = _clean_text(metadata.get("session_id"), limit=140)
    memory_user = _clean_text(metadata.get("user_id") or metadata.get("username"), limit=140)
    profile_user = _profile_value(user_profile, "id", "username")

    if memory_session and memory_session == session_id:
        return True
    if memory_user and profile_user and memory_user == profile_user:
        return True
    return not memory_session and not memory_user


def _relevant_vector_memories(
    user_input: str,
    *,
    session_id: str,
    user_profile: Dict[str, Any],
) -> List[str]:
    try:
        raw_items = search_memory(user_input, n_results=MAX_RELEVANT_MEMORIES + 3)
    except Exception:
        return []

    lines: List[str] = []
    for item in raw_items:
        if not isinstance(item, dict) or not _query_matches_memory_scope(item, session_id=session_id, user_profile=user_profile):
            continue
        text = _clean_text(item.get("text"), limit=180)
        if text:
            lines.append(text)
        if len(lines) >= MAX_RELEVANT_MEMORIES:
            break
    return _dedupe(lines)


def _working_memory_lines(memory: WorkingMemoryState) -> List[str]:
    lines: List[str] = []
    if memory.active_topic:
        lines.append(f"active topic: {_clean_text(memory.active_topic, limit=100)}")
    if memory.current_goal:
        lines.append(f"current goal: {_clean_text(memory.current_goal, limit=100)}")
    if memory.last_agent:
        lines.append(f"last useful agent: {_clean_text(memory.last_agent, limit=60)}")
    recent_refs = [_clean_text(item, limit=70) for item in list(memory.recent_references or [])[-3:]]
    recent_refs = [item for item in recent_refs if item]
    if recent_refs:
        lines.append("recent references: " + ", ".join(recent_refs))
    return lines


def _history_hint(history: Iterable[Dict[str, str]]) -> str:
    messages = [
        _clean_text(item.get("content"), limit=120)
        for item in history
        if str(item.get("role") or "").lower() == "user" and _clean_text(item.get("content"), limit=120)
    ]
    if len(messages) < 2:
        return ""
    return "recent user flow: " + " -> ".join(messages[-3:])


def _behavior_pattern(data: Dict[str, Any]) -> str:
    stats = data.get("behavior_stats") if isinstance(data.get("behavior_stats"), dict) else {}
    counts = {
        "short": int(stats.get("short_queries") or 0),
        "medium": int(stats.get("medium_queries") or 0),
        "long": int(stats.get("long_queries") or 0),
    }
    total = sum(counts.values())
    if total < 4:
        return ""
    label, count = max(counts.items(), key=lambda item: item[1])
    if count / max(total, 1) < 0.45:
        return ""
    return f"usually sends {label} requests"


def _topic_patterns(data: Dict[str, Any]) -> List[str]:
    frequency = data.get("topic_frequency") if isinstance(data.get("topic_frequency"), dict) else {}
    top = Counter({str(key): int(value) for key, value in frequency.items() if str(key).strip()}).most_common(3)
    return [f"{topic} ({count})" for topic, count in top if count > 1]


def _smart_suggestion(intent: str, user_input: str, context: Dict[str, Any]) -> Optional[str]:
    normalized_intent = str(intent or "").strip().lower()
    text = str(user_input or "").strip().lower()
    if not text or normalized_intent in {"greeting", "conversation", "memory", "permission"}:
        return None
    if any(marker in text for marker in ("suggest", "next", "what should", "recommend")):
        return None

    topics = context.get("top_topics") or []
    if normalized_intent in {"document", "write"} or any(marker in text for marker in ("assignment", "notes", "write")):
        return "I can also turn this into a clean outline or revision notes if that helps."
    if normalized_intent in {"code", "coding"} or "code" in text:
        return "I can help you add a quick test plan next."
    if normalized_intent in {"research", "summarize"}:
        return "I can condense this into action points when you are ready."
    if topics:
        return f"Based on your recent pattern around {topics[0]}, I can keep the next step focused."
    return None


def _dedupe(items: Iterable[str]) -> List[str]:
    seen = set()
    output: List[str] = []
    for item in items:
        text = _clean_text(item)
        key = text.lower()
        if not text or key in seen:
            continue
        seen.add(key)
        output.append(text)
    return output


def build_personal_context(
    user_input: str,
    *,
    session_id: str = "default",
    user_profile: Optional[Dict[str, Any]] = None,
    history: Optional[List[Dict[str, str]]] = None,
    intent: str = "general",
) -> Dict[str, Any]:
    profile = dict(user_profile or {})
    normalized_session = str(session_id or "default").strip() or "default"
    learning_data = _load_learning_snapshot()
    working_memory = load_working_memory(normalized_session)

    display_name = get_personal_display_name(profile)
    city = _profile_value(profile, "city") or _semantic_value("user_city") or _clean_text(get_user_city(), limit=100)
    age = _profile_value(profile, "age") or _semantic_value("user_age") or _clean_text(get_user_age(), limit=40)
    preferences = _dedupe(_extract_semantic_preferences() + _extract_learning_preferences(learning_data))[:5]
    relevant_memories = _relevant_vector_memories(user_input, session_id=normalized_session, user_profile=profile)
    history_line = _history_hint(history or [])
    pattern = _behavior_pattern(learning_data)
    top_topics = _topic_patterns(learning_data)

    context: Dict[str, Any] = {
        "display_name": display_name,
        "city": city,
        "age": age,
        "preferences": preferences,
        "working_memory": _working_memory_lines(working_memory),
        "relevant_memories": relevant_memories,
        "history_hint": history_line,
        "behavior_pattern": pattern,
        "top_topics": top_topics,
    }
    suggestion = _smart_suggestion(intent, user_input, context)
    if suggestion:
        context["suggestion"] = suggestion
    return context


def personal_context_lines(context: Dict[str, Any]) -> List[str]:
    lines: List[str] = []
    if context.get("display_name"):
        lines.append(f"user name: {context['display_name']}")
    if context.get("city"):
        lines.append(f"user city: {context['city']}")
    if context.get("preferences"):
        lines.append("preferences: " + "; ".join(list(context["preferences"])[:4]))
    if context.get("behavior_pattern"):
        lines.append(f"pattern: {context['behavior_pattern']}")
    if context.get("top_topics"):
        lines.append("recurring topics: " + ", ".join(list(context["top_topics"])[:3]))
    if context.get("working_memory"):
        lines.extend(f"working memory: {item}" for item in list(context["working_memory"])[:3])
    if context.get("history_hint"):
        lines.append(str(context["history_hint"]))
    if context.get("relevant_memories"):
        lines.extend(f"relevant memory: {item}" for item in list(context["relevant_memories"])[:MAX_RELEVANT_MEMORIES])
    return lines[:MAX_CONTEXT_LINES]


def build_personalized_system_prompt(base_prompt: str, context: Optional[Dict[str, Any]]) -> str:
    lines = personal_context_lines(context or {})
    if not lines:
        return str(base_prompt or "").strip()
    personal_block = "\n".join(f"- {line}" for line in lines)
    return (
        f"{str(base_prompt or '').strip()}\n\n"
        "PERSONAL CONTEXT (use quietly and only when relevant):\n"
        f"{personal_block}\n\n"
        "PERSONALIZATION RULES:\n"
        "- Use the user's name only when it feels natural, especially greetings or direct preference references.\n"
        "- Prefer the user's stated style/preferences when they apply.\n"
        "- Use recent context to avoid repeating explanations.\n"
        "- Do not mention memory, profiles, or stored data unless the user asks."
    ).strip()


def append_relevant_suggestion(response: str, context: Optional[Dict[str, Any]]) -> str:
    text = str(response or "").strip()
    suggestion = _clean_text((context or {}).get("suggestion"), limit=180)
    if not text or not suggestion:
        return text
    lowered = text.lower()
    if "if you want" in lowered or "next, i can" in lowered or suggestion.lower() in lowered:
        return text
    if suggestion.startswith("I "):
        suggestion_text = suggestion
    else:
        suggestion_text = suggestion[0].lower() + suggestion[1:] if len(suggestion) > 1 else suggestion
    return f"{text}\n\nNext, {suggestion_text}"


def remember_profile_identity(user_profile: Optional[Dict[str, Any]]) -> None:
    profile = dict(user_profile or {})
    name = _profile_value(profile, "preferred_name", "name", "username")
    if name and name.lower() not in {"guest", "public"}:
        remember_fact("user_name", name, confidence=0.95, source="profile")


def remember_explicit_personal_signals(user_input: str) -> None:
    text = str(user_input or "").strip()
    lowered = text.lower()
    name_match = re.search(r"\b(?:my name is|call me)\s+([a-zA-Z][a-zA-Z ]{0,39})\b", text, flags=re.IGNORECASE)
    if name_match:
        remember_fact("user_name", name_match.group(1).strip().title(), confidence=1.0, source="explicit_user_signal")
    if re.search(r"\b(?:i prefer|i usually|my preference is|default to)\b", lowered):
        remember_fact("user_preference", text, confidence=0.86, source="explicit_user_signal")
