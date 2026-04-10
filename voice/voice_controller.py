from __future__ import annotations

from typing import Any, Dict

from voice.audio_manager import get_audio_status
from voice.mic_handler import get_microphone_status
from voice.noise_filter import analyze_transcript_noise, clean_transcript_text
from voice.speech_to_text import get_stt_status, transcribe_audio_file, transcribe_microphone
from voice.text_to_speech import list_voices, speak_text, stop_speaking, tts_available
from voice.voice_config import list_voice_personas, load_voice_settings, update_voice_settings
from voice.wake_word import detect_wake_word


def get_voice_status() -> Dict[str, Any]:
    settings = load_voice_settings()
    return {
        "mode": "hybrid",
        "settings": settings.to_dict(),
        "tts": {"available": tts_available(), "voices": list_voices()[:8]},
        "stt": get_stt_status(),
        "microphone": get_microphone_status(),
        "audio": get_audio_status(),
        "personas": list_voice_personas(),
        "wake_word_preview": detect_wake_word("hey aura status check", settings.wake_words),
    }


def update_voice_preferences(**updates: object) -> Dict[str, Any]:
    settings = update_voice_settings(**updates)
    return {"success": True, "settings": settings.to_dict()}


def speak_response(text: str) -> Dict[str, Any]:
    return speak_text(text)


def stop_voice_output() -> Dict[str, Any]:
    return stop_speaking()


def transcribe_file_request(path_value: str) -> Dict[str, Any]:
    result = transcribe_audio_file(path_value)
    if result.get("success") and result.get("text"):
        result["cleaned_text"] = clean_transcript_text(str(result["text"]))
        result["wake_word"] = detect_wake_word(result["cleaned_text"])
        result["quality"] = analyze_transcript_noise(str(result["text"]))
    return result


def transcribe_microphone_request(*, timeout: int = 5, phrase_time_limit: int | None = None) -> Dict[str, Any]:
    result = transcribe_microphone(timeout=timeout, phrase_time_limit=phrase_time_limit)
    if result.get("success") and result.get("text"):
        result["cleaned_text"] = clean_transcript_text(str(result["text"]))
        result["wake_word"] = detect_wake_word(result["cleaned_text"])
        result["quality"] = analyze_transcript_noise(str(result["text"]))
    return result
