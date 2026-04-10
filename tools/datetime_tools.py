from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Dict, List


TIME_PATTERN = re.compile(r"\b(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)\b", re.IGNORECASE)


def parse_temporal_entities(text: str) -> Dict[str, List[str]]:
    lowered = str(text or "").lower()
    dates: List[str] = []
    times: List[str] = []

    if "today" in lowered:
        dates.append(datetime.now().strftime("%Y-%m-%d"))
    if "tomorrow" in lowered:
        dates.append((datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"))
    if "yesterday" in lowered:
        dates.append((datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"))
    if "next week" in lowered:
        dates.append((datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d"))

    explicit_dates = re.findall(r"\b\d{4}-\d{2}-\d{2}\b", lowered)
    dates.extend(explicit_dates)

    for match in TIME_PATTERN.finditer(lowered):
        times.append(match.group(1).strip())

    return {
        "dates": _unique(dates),
        "times": _unique(times),
    }


def _unique(values: List[str]) -> List[str]:
    seen = set()
    result = []
    for value in values:
        normalized = str(value or "").strip()
        if not normalized:
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result
