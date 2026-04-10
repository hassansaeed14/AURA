from __future__ import annotations

import re
from typing import Dict


NOISE_PATTERNS = [
    r"\b(um+|uh+|hmm+|ah+)\b",
    r"\b(background noise|static)\b",
]

SUPPORTIVE_REPLACEMENTS = {
    "plz": "please",
    "pls": "please",
    "u": "you",
    "ur": "your",
}


def clean_transcript_text(text: str) -> str:
    cleaned = str(text or "").strip()
    for pattern in NOISE_PATTERNS:
        cleaned = re.sub(pattern, " ", cleaned, flags=re.IGNORECASE)
    for short_form, expanded in SUPPORTIVE_REPLACEMENTS.items():
        cleaned = re.sub(rf"\b{re.escape(short_form)}\b", expanded, cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*([,.;:!?])\s*", r"\1 ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def analyze_transcript_noise(text: str) -> Dict[str, object]:
    original = str(text or "")
    cleaned = clean_transcript_text(original)
    return {
        "original_length": len(original),
        "cleaned_length": len(cleaned),
        "changed": original.strip() != cleaned.strip(),
        "cleaned_text": cleaned,
        "removed_fillers": max(0, len(original.split()) - len(cleaned.split())),
        "quality": estimate_transcript_quality(original, cleaned),
    }


def estimate_transcript_quality(original: str, cleaned: str) -> str:
    if not cleaned.strip():
        return "poor"
    if len(cleaned) >= max(4, int(len(original or "") * 0.7)):
        return "good"
    if len(cleaned) >= max(2, int(len(original or "") * 0.4)):
        return "fair"
    return "poor"
