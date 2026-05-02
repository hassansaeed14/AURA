from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Dict, List, Tuple

from brain.understanding_engine import clean_user_input
from config.limits_config import MAX_MULTI_COMMANDS


CONNECTOR_PATTERNS: Tuple[str, ...] = (
    r"\s+and then\s+",
    r"\s+then\s+",
    r"\s+also\s+",
    r"\s+after that\s+",
    r"\s*;\s*",
    r"\s*\n+\s*",
)

ACTION_PREFIXES: Tuple[str, ...] = (
    "open",
    "go",
    "visit",
    "navigate",
    "rerun",
    "repeat",
    "type",
    "press",
    "hit",
    "use",
    "scroll",
    "focus",
    "switch",
    "remind",
    "translate",
    "summarize",
    "make",
    "create",
    "save",
    "search",
    "research",
    "study",
    "explain",
    "write",
    "send",
    "read",
    "analyze",
    "show",
    "list",
    "add",
    "delete",
    "remove",
    "compare",
    "find",
    "calculate",
)

PROTECTED_PATTERNS: Tuple[str, ...] = (
    r"\bdifference between .+ and .+",
    r"\bcompare .+ and .+",
    r"\bbetween [a-z0-9 ]+ and [a-z0-9 ]+",
)


@dataclass(frozen=True)
class CommandSplitResult:
    original: str
    normalized: str
    commands: List[str]
    connectors_used: List[str]

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


def _is_meaningful(text: str) -> bool:
    return bool(str(text or "").strip(" ,.;:!?"))


def _matches_protected_pattern(text: str) -> bool:
    lowered = text.lower()
    return any(re.search(pattern, lowered) for pattern in PROTECTED_PATTERNS)


def _looks_like_command(fragment: str) -> bool:
    lowered = fragment.strip().lower()
    if not lowered:
        return False
    if lowered.startswith(("remind me", "what", "who", "how", "when")):
        return True
    return lowered.split(" ", 1)[0] in ACTION_PREFIXES


def _split_by_regex(parts: List[str], pattern: str) -> List[str]:
    updated: List[str] = []
    for part in parts:
        fragments = [item.strip(" ,") for item in re.split(pattern, part, flags=re.IGNORECASE) if _is_meaningful(item)]
        if len(fragments) > 1:
            updated.extend(fragments)
        else:
            updated.append(part.strip(" ,"))
    return updated


def _split_on_commas(part: str) -> List[str]:
    raw_fragments = [item.strip(" ,") for item in part.split(",") if _is_meaningful(item)]
    if len(raw_fragments) < 2:
        return [part.strip(" ,")]

    if sum(1 for item in raw_fragments if _looks_like_command(item)) < 2:
        return [part.strip(" ,")]

    return raw_fragments


def _split_on_and(part: str) -> List[str]:
    lowered = part.lower()
    if " and " not in lowered or _matches_protected_pattern(lowered):
        return [part.strip(" ,")]

    left, right = part.split(" and ", 1)
    left = left.strip(" ,")
    right = right.strip(" ,")

    if not _is_meaningful(left) or not _is_meaningful(right):
        return [part.strip(" ,")]

    if _looks_like_command(left) and _looks_like_command(right):
        return [left, *_split_on_and(right)]

    if right.lower().startswith(("remind me", "save", "make", "create", "translate", "open", "go to", "visit", "navigate", "rerun", "repeat", "type", "press", "hit", "use", "scroll", "focus", "switch")):
        return [left, *_split_on_and(right)]

    return [part.strip(" ,")]


def split_commands(text: str, *, max_commands: int = MAX_MULTI_COMMANDS) -> List[str]:
    normalized = clean_user_input(text)
    if not _is_meaningful(normalized):
        return []

    if _matches_protected_pattern(normalized):
        return [normalized]

    parts = [normalized]
    for pattern in CONNECTOR_PATTERNS:
        parts = _split_by_regex(parts, pattern)

    comma_split: List[str] = []
    for part in parts:
        comma_split.extend(_split_on_commas(part))

    final_parts: List[str] = []
    for part in comma_split:
        final_parts.extend(_split_on_and(part))

    cleaned: List[str] = []
    seen = set()
    for part in final_parts:
        normalized_part = re.sub(r"\s+", " ", part).strip(" ,")
        if not _is_meaningful(normalized_part):
            continue
        key = normalized_part.lower()
        if key in seen:
            continue
        cleaned.append(normalized_part)
        seen.add(key)

    return cleaned[:max_commands]


def split_commands_detailed(text: str) -> CommandSplitResult:
    normalized = clean_user_input(text)
    connectors_used = [pattern.strip("\\s+") for pattern in CONNECTOR_PATTERNS if re.search(pattern, normalized, flags=re.IGNORECASE)]
    return CommandSplitResult(
        original=str(text or ""),
        normalized=normalized,
        commands=split_commands(normalized),
        connectors_used=connectors_used,
    )
