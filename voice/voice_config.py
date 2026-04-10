from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


VOICE_SETTINGS_FILE = Path("memory/voice_settings.json")


@dataclass(slots=True)
class VoiceSettings:
    persona: str = "jarvis_inspired"
    language: str = "en-US"
    voice_gender: str = "neutral"
    rate: float = 1.0
    volume: float = 1.0
    wake_words: List[str] = field(default_factory=lambda: ["hey aura", "aura"])
    wake_word_sensitivity: float = 0.7
    phrase_time_limit: int = 8
    ambient_noise_adjustment: bool = True
    backend: str = "local_hybrid"
    enabled: bool = True
    auto_speak_responses: bool = False
    preferred_input_device: Optional[str] = None
    preferred_output_device: Optional[str] = None
    preferred_provider: Optional[str] = None

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


VOICE_PERSONAS = {
    "jarvis_inspired": {
        "name": "Jarvis Inspired",
        "description": "Calm, precise, composed, and quietly proactive.",
    },
    "warm_guide": {
        "name": "Warm Guide",
        "description": "Supportive, clear, and conversational.",
    },
    "developer": {
        "name": "Developer",
        "description": "Direct, technical, and detail-aware.",
    },
}


def load_voice_settings() -> VoiceSettings:
    if not VOICE_SETTINGS_FILE.exists():
        return VoiceSettings()
    try:
        payload = json.loads(VOICE_SETTINGS_FILE.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            return VoiceSettings()
        defaults = VoiceSettings().to_dict()
        defaults.update(payload)
        return VoiceSettings(**defaults)
    except Exception:
        return VoiceSettings()


def save_voice_settings(settings: VoiceSettings) -> VoiceSettings:
    VOICE_SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    VOICE_SETTINGS_FILE.write_text(json.dumps(settings.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    return settings


def update_voice_settings(**updates: object) -> VoiceSettings:
    settings = load_voice_settings()
    for key, value in updates.items():
        if hasattr(settings, key) and value is not None:
            if key == "wake_words" and isinstance(value, str):
                value = [item.strip().lower() for item in value.split(",") if item.strip()]
            setattr(settings, key, value)
    return save_voice_settings(settings)


def list_voice_personas() -> List[Dict[str, str]]:
    return [{"id": key, **value} for key, value in VOICE_PERSONAS.items()]
