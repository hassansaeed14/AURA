from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Dict, List

from brain.intent_engine import detect_intent_with_confidence, normalize_text


INTENT_RULES: Dict[str, List[str]] = {
    "translation": ["translate", "how to say"],
    "weather": ["weather", "forecast", "temperature"],
    "news": ["news", "headlines"],
    "task": ["task", "todo", "to do"],
    "reminder": ["remind me", "reminder"],
    "web_search": ["search", "google", "look up"],
    "file": ["file", "pdf", "document"],
    "code": ["code", "debug", "script", "python"],
    "research": ["research", "analyze", "investigate"],
    "summarize": ["summarize", "summary"],
    "study": ["study", "teach", "explain"],
    "currency": ["usd", "pkr", "eur", "btc", "eth"],
    "math": ["calculate", "solve", "+", "-", "*", "/"],
}


@dataclass(slots=True)
class ConfidenceReport:
    intent: str
    confidence: float
    matched_rules: List[str] = field(default_factory=list)
    fallback_reason: str = ""
    ambiguity_flag: bool = False
    candidates: List[Dict[str, object]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


def evaluate_confidence(command: str) -> ConfidenceReport:
    normalized = normalize_text(command)
    intent, confidence = detect_intent_with_confidence(normalized)

    candidates = []
    for candidate_intent, phrases in INTENT_RULES.items():
        matches = [phrase for phrase in phrases if phrase in normalized]
        if matches:
            candidates.append(
                {
                    "intent": candidate_intent,
                    "score": len(matches),
                    "matched_rules": matches,
                }
            )

    candidates.sort(key=lambda item: item["score"], reverse=True)
    ambiguity = len(candidates) > 1 and abs(int(candidates[0]["score"]) - int(candidates[1]["score"])) <= 1
    matched_rules = []
    for item in candidates:
        if item["intent"] == intent:
            matched_rules = list(item["matched_rules"])
            break

    fallback_reason = ""
    if intent == "general" and not candidates:
        fallback_reason = "no_matching_rules"
    elif ambiguity:
        fallback_reason = "ambiguous_intent_candidates"
    elif confidence < 0.35:
        fallback_reason = "confidence_below_threshold"

    return ConfidenceReport(
        intent=intent,
        confidence=confidence,
        matched_rules=matched_rules,
        fallback_reason=fallback_reason,
        ambiguity_flag=ambiguity,
        candidates=candidates[:5],
    )
