from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional

from tools.datetime_tools import parse_temporal_entities


LANGUAGES = (
    "english",
    "urdu",
    "arabic",
    "hindi",
    "punjabi",
    "french",
    "spanish",
    "german",
    "turkish",
    "chinese",
)

APP_NAMES = (
    "chrome",
    "edge",
    "firefox",
    "vscode",
    "notepad",
    "word",
    "excel",
    "powerpoint",
    "whatsapp",
    "instagram",
    "youtube",
)

FILE_PATTERN = re.compile(r"(?:[A-Za-z]:\\[^\s]+|[\w\-. ]+\.(?:pdf|docx?|txt|csv|xlsx|pptx|json|py|js|html|css|md))", re.IGNORECASE)
URL_PATTERN = re.compile(r"(https?://\S+|www\.\S+)", re.IGNORECASE)
USERNAME_PATTERN = re.compile(r"@([a-zA-Z0-9_.-]+)|\busername\s+([a-zA-Z0-9_.-]+)", re.IGNORECASE)
CURRENCY_PATTERN = re.compile(r"\b(?:USD|PKR|EUR|GBP|INR|AED|SAR|BTC|ETH|dollars?|rupees?|euros?|pounds?)\b", re.IGNORECASE)
AMOUNT_PATTERN = re.compile(r"\b\d+(?:\.\d+)?\b")


@dataclass(slots=True)
class EntityParseResult:
    dates: List[str] = field(default_factory=list)
    times: List[str] = field(default_factory=list)
    reminder_text: Optional[str] = None
    urls: List[str] = field(default_factory=list)
    files: List[str] = field(default_factory=list)
    apps: List[str] = field(default_factory=list)
    currencies: List[str] = field(default_factory=list)
    amounts: List[str] = field(default_factory=list)
    topics: List[str] = field(default_factory=list)
    languages: List[str] = field(default_factory=list)
    usernames: List[str] = field(default_factory=list)
    primary_topic: Optional[str] = None

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


def _unique(values: List[str]) -> List[str]:
    seen = set()
    result = []
    for value in values:
        normalized = str(value or "").strip()
        if not normalized:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(normalized)
    return result


def _extract_languages(command: str) -> List[str]:
    lowered = command.lower()
    return [language for language in LANGUAGES if re.search(rf"\b{re.escape(language)}\b", lowered)]


def _extract_apps(command: str) -> List[str]:
    lowered = command.lower()
    return [app for app in APP_NAMES if re.search(rf"\b{re.escape(app)}\b", lowered)]


def _extract_usernames(command: str) -> List[str]:
    matches = USERNAME_PATTERN.findall(command)
    usernames = []
    for left, right in matches:
        usernames.append(left or right)
    return _unique(usernames)


def _extract_topics(command: str, result: EntityParseResult) -> List[str]:
    cleaned = command
    for value in result.urls + result.files + result.apps + result.currencies + result.amounts + result.languages + result.usernames:
        cleaned = cleaned.replace(value, " ")

    cleaned = re.sub(r"\b(remind me to|translate|open|save|research|summarize|make|create|add|set|show|find)\b", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b(today|tomorrow|yesterday|next week|next month|at \d{1,2}(?::\d{2})?\s*(?:am|pm)?)\b", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,.")
    if not cleaned:
        return []
    return [cleaned]


def _normalize_file_matches(matches: List[str]) -> List[str]:
    cleaned = []
    for match in matches:
        value = str(match).strip()
        parts = [
            item.strip()
            for item in re.split(
                r"\b(?:and|then|also|open|read|summarize|analyze|translate|save|show|list|find|review|create|make)\b",
                value,
                flags=re.IGNORECASE,
            )
            if item.strip()
        ]
        if parts:
            value = parts[-1]
        cleaned.append(value.strip())
    return _unique(cleaned)


def parse_entities(command: str) -> EntityParseResult:
    text = str(command or "").strip()
    temporal = parse_temporal_entities(text)
    result = EntityParseResult(
        dates=_unique(temporal.get("dates", [])),
        times=_unique(temporal.get("times", [])),
        urls=_unique(URL_PATTERN.findall(text)),
        files=_normalize_file_matches(FILE_PATTERN.findall(text)),
        apps=_unique(_extract_apps(text)),
        currencies=_unique([match.group(0).upper() for match in CURRENCY_PATTERN.finditer(text)]),
        amounts=_unique([match.group(0) for match in AMOUNT_PATTERN.finditer(text)]),
        languages=_unique(_extract_languages(text)),
        usernames=_unique(_extract_usernames(text)),
    )

    reminder_match = re.search(r"remind me to\s+(.+)$", text, flags=re.IGNORECASE)
    if reminder_match:
        reminder_text = reminder_match.group(1)
        for value in result.dates + result.times:
            reminder_text = re.sub(rf"\b{re.escape(value)}\b", "", reminder_text, flags=re.IGNORECASE)
        reminder_text = re.sub(r"\b(today|tomorrow|yesterday|next week|next month)\b", "", reminder_text, flags=re.IGNORECASE)
        reminder_text = re.sub(r"\bat\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)?\b", "", reminder_text, flags=re.IGNORECASE)
        reminder_text = re.sub(r"\bat\b\s*$", "", reminder_text, flags=re.IGNORECASE)
        result.reminder_text = reminder_text.strip(" ,.")

    result.topics = _unique(_extract_topics(text, result))
    result.primary_topic = result.topics[0] if result.topics else None
    return result
