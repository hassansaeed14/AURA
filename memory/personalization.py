from __future__ import annotations

import re
from collections import Counter
from typing import Any, Dict, Iterable, List, Optional

from memory.semantic_memory import list_facts, recall_fact, remember_fact
from memory.vector_memory import search_memory
from memory.working_memory import WorkingMemoryState, load_working_memory


MAX_CONTEXT_LINES = 9
MAX_RELEVANT_MEMORIES = 3
PUBLIC_SESSION_PERSONAL_FACTS: Dict[str, Dict[str, str]] = {}
UNSCOPED_SESSION_IDS = {"", "default", "runtime"}
RESERVED_IDENTITY_VALUES = {"guest", "public", "anonymous", "unknown", "none", "null"}


def _normalize_memory_scope(value: Any) -> str:
    text = _clean_text(value, limit=120).strip().lower()
    if not text or text in RESERVED_IDENTITY_VALUES:
        return ""
    return re.sub(r"[^a-z0-9_.:-]+", "_", text).strip("_")


def _profile_user_id(profile: Dict[str, Any]) -> str:
    for key in ("id", "user_id", "username"):
        scope = _normalize_memory_scope(profile.get(key))
        if scope:
            return scope
    return ""


def is_authenticated_user_profile(user_profile: Optional[Dict[str, Any]] = None) -> bool:
    return bool(_profile_user_id(dict(user_profile or {})))


def _is_safe_public_session(session_id: str) -> bool:
    normalized = _normalize_memory_scope(session_id)
    return bool(normalized and normalized not in UNSCOPED_SESSION_IDS)


def _scoped_semantic_key(scope_id: str, key: str) -> str:
    return f"user:{_normalize_memory_scope(scope_id)}:{str(key or '').strip().lower()}"


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


def _scoped_semantic_value(profile: Dict[str, Any], key: str) -> str:
    scope_id = _profile_user_id(profile)
    if not scope_id:
        return ""
    return _semantic_value(_scoped_semantic_key(scope_id, key))


def _session_fact(session_id: str, key: str) -> str:
    if not _is_safe_public_session(session_id):
        return ""
    bucket = PUBLIC_SESSION_PERSONAL_FACTS.get(_normalize_memory_scope(session_id), {})
    return _clean_text(bucket.get(str(key or "").strip().lower()), limit=140)


def get_personal_display_name(
    user_profile: Optional[Dict[str, Any]] = None,
    *,
    allow_memory_fallback: bool = True,
    session_id: Optional[str] = None,
) -> str:
    profile = dict(user_profile or {})
    profile_name = _profile_value(profile, "preferred_name", "name")
    if profile_name and profile_name.lower() not in {"guest", "public"}:
        return _display_name(profile_name)

    if not allow_memory_fallback:
        return ""

    if is_authenticated_user_profile(profile):
        scoped_name = _scoped_semantic_value(profile, "user_name")
        if scoped_name:
            return _display_name(scoped_name)
        username = _profile_value(profile, "username")
        return _display_name(username) if username.lower() not in {"guest", "public"} else ""

    return _display_name(_session_fact(str(session_id or ""), "user_name"))

    return ""


def _load_learning_snapshot() -> Dict[str, Any]:
    # The historical learning file is global and not user-scoped. Keep it out
    # of live personalization until it can be migrated with owner metadata.
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


def _extract_semantic_preferences(
    *,
    session_id: str,
    user_profile: Dict[str, Any],
) -> List[str]:
    preferences: List[str] = []
    scope_id = _profile_user_id(user_profile)
    if not scope_id:
        session_preference = _session_fact(session_id, "user_preference")
        return [session_preference] if session_preference else []

    scoped_prefix = _scoped_semantic_key(scope_id, "")
    for fact in list_facts():
        key = str(fact.get("key") or "")
        value = _clean_text(fact.get("value"), limit=140)
        if not key.startswith(scoped_prefix):
            continue
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
    memory_user = _normalize_memory_scope(metadata.get("user_id") or metadata.get("username"))
    profile_user = _profile_user_id(user_profile)

    if memory_user and profile_user and memory_user == profile_user:
        return True
    return False


def _relevant_vector_memories(
    user_input: str,
    *,
    session_id: str,
    user_profile: Dict[str, Any],
) -> List[str]:
    if not is_authenticated_user_profile(user_profile):
        return []

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
    authenticated = is_authenticated_user_profile(profile)
    working_memory = load_working_memory(normalized_session) if authenticated else WorkingMemoryState()

    display_name = get_personal_display_name(profile, session_id=normalized_session)
    city = _profile_value(profile, "city") or _scoped_semantic_value(profile, "user_city")
    age = _profile_value(profile, "age") or _scoped_semantic_value(profile, "user_age")
    preferences = _dedupe(
        _extract_semantic_preferences(session_id=normalized_session, user_profile=profile)
        + (_extract_learning_preferences(learning_data) if authenticated else [])
    )[:5]
    relevant_memories = _relevant_vector_memories(user_input, session_id=normalized_session, user_profile=profile)
    history_line = _history_hint(history or [])
    pattern = _behavior_pattern(learning_data) if authenticated else ""
    top_topics = _topic_patterns(learning_data) if authenticated else []

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


def clear_session_personal_context(session_id: Optional[str] = None) -> None:
    if session_id is None:
        PUBLIC_SESSION_PERSONAL_FACTS.clear()
        return
    PUBLIC_SESSION_PERSONAL_FACTS.pop(_normalize_memory_scope(session_id), None)


def remember_profile_identity(user_profile: Optional[Dict[str, Any]]) -> None:
    profile = dict(user_profile or {})
    scope_id = _profile_user_id(profile)
    if not scope_id:
        return
    name = _profile_value(profile, "preferred_name", "name")
    if name and name.lower() not in {"guest", "public"}:
        remember_fact(_scoped_semantic_key(scope_id, "user_name"), name, confidence=0.95, source="profile")


def _extract_explicit_name(user_input: str) -> str:
    text = str(user_input or "").strip()
    name_match = re.search(
        r"\b(?:my name is|call me)\s+([a-zA-Z][a-zA-Z .'-]{0,39})",
        text,
        flags=re.IGNORECASE,
    )
    if not name_match:
        return ""
    candidate = re.split(r"\b(?:and|but|then)\b|[,.!?]", name_match.group(1).strip(), maxsplit=1, flags=re.IGNORECASE)[0]
    return _display_name(candidate.strip())


def _remember_session_fact(session_id: str, key: str, value: str) -> None:
    if not _is_safe_public_session(session_id):
        return
    scope = _normalize_memory_scope(session_id)
    bucket = PUBLIC_SESSION_PERSONAL_FACTS.setdefault(scope, {})
    bucket[str(key or "").strip().lower()] = _clean_text(value, limit=180)


def remember_explicit_personal_signals(
    user_input: str,
    *,
    session_id: str = "default",
    user_profile: Optional[Dict[str, Any]] = None,
) -> None:
    text = str(user_input or "").strip()
    lowered = text.lower()
    profile = dict(user_profile or {})
    scope_id = _profile_user_id(profile)
    name = _extract_explicit_name(text)
    preference_signal = bool(re.search(r"\b(?:i prefer|i usually|my preference is|default to)\b", lowered))

    if scope_id:
        if name:
            remember_fact(_scoped_semantic_key(scope_id, "user_name"), name, confidence=1.0, source="explicit_user_signal")
        if preference_signal:
            remember_fact(_scoped_semantic_key(scope_id, "user_preference"), text, confidence=0.86, source="explicit_user_signal")
        return

    if name:
        _remember_session_fact(session_id, "user_name", name)
    if preference_signal:
        _remember_session_fact(session_id, "user_preference", text)
