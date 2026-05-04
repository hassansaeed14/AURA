from __future__ import annotations

from typing import Any, Dict

from voice.desktop_voice_runtime import get_desktop_voice_status
from voice.voice_controller import get_voice_status


WAKE_PHRASE = "hey aura"


def get_desktop_voice_runtime_status() -> Dict[str, Any]:
    status = get_desktop_voice_status()
    return {
        **status,
        "label": "Desktop voice",
        "states": ["idle", "listening", "awake", "processing", "speaking", "error"],
        "truth_note": (
            "Desktop wake listening starts only after the user explicitly enables it. "
            "Browser push-to-talk remains separate."
        ),
    }


def get_assistant_runtime_status() -> Dict[str, Any]:
    voice_status = get_voice_status()
    tts = voice_status.get("tts") or {}
    settings = voice_status.get("settings") or {}
    desktop_voice = get_desktop_voice_runtime_status()
    return {
        "success": True,
        "wake_phrase": WAKE_PHRASE,
        "default_mode": "text",
        "active_mode": "text",
        "modes": {
            "text": {
                "label": "Text mode",
                "available": True,
                "active": True,
                "requires_microphone": False,
                "message": "Text mode is always available.",
            },
            "push_to_talk": {
                "label": "Push-to-talk",
                "available": True,
                "active": False,
                "requires_microphone": True,
                "client_managed": True,
                "message": "Browser push-to-talk is available when SpeechRecognition and mic permission are available.",
            },
            "desktop_voice": desktop_voice,
        },
        "voice_runtime": desktop_voice,
        "tts": {
            "provider": tts.get("provider") or "browser_speech_synthesis",
            "available": bool(tts.get("available", True)),
            "client_managed": True,
            "backend_enabled": False,
            "auto_speak_responses": bool(settings.get("auto_speak_responses")),
            "message": tts.get("message") or "AURA speaks through browser speech synthesis.",
        },
        "safety": {
            "always_on_browser_wake": False,
            "requires_user_enabled_voice": True,
            "critical_actions_blocked_or_verified": True,
        },
    }
