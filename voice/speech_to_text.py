from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from voice.voice_config import load_voice_settings

try:
    import speech_recognition as sr  # type: ignore
except Exception:  # pragma: no cover
    sr = None


def stt_available() -> bool:
    return sr is not None


def get_stt_status() -> Dict[str, Any]:
    return {
        "available": stt_available(),
        "backend": "speech_recognition" if stt_available() else "unavailable",
        "supports_microphone": stt_available(),
        "supports_file_transcription": stt_available(),
    }


def _prepare_recognizer(recognizer):
    settings = load_voice_settings()
    recognizer.dynamic_energy_threshold = bool(settings.ambient_noise_adjustment)
    return recognizer


def transcribe_audio_file(path_value: str) -> Dict[str, Any]:
    if sr is None:
        return {"success": False, "status": "unavailable", "message": "Speech recognition backend is not available."}

    path = Path(path_value).expanduser().resolve()
    if not path.exists():
        return {"success": False, "status": "missing_file", "message": str(path)}

    recognizer = sr.Recognizer()
    settings = load_voice_settings()
    try:
        recognizer = _prepare_recognizer(recognizer)
        with sr.AudioFile(str(path)) as source:
            audio = recognizer.record(source)
        text = recognizer.recognize_google(audio, language=settings.language)
        return {"success": True, "status": "transcribed", "text": text, "source": "file"}
    except Exception as error:
        return {"success": False, "status": "transcription_error", "message": str(error)}


def transcribe_microphone(*, timeout: int = 5, phrase_time_limit: int | None = None) -> Dict[str, Any]:
    if sr is None:
        return {"success": False, "status": "unavailable", "message": "Speech recognition backend is not available."}

    recognizer = _prepare_recognizer(sr.Recognizer())
    settings = load_voice_settings()
    limit = int(phrase_time_limit or settings.phrase_time_limit)
    try:
        with sr.Microphone() as source:
            if settings.ambient_noise_adjustment:
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=limit)
        text = recognizer.recognize_google(audio, language=settings.language)
        return {"success": True, "status": "transcribed", "text": text, "source": "microphone"}
    except Exception as error:
        return {"success": False, "status": "transcription_error", "message": str(error), "source": "microphone"}


def listen(*, timeout: int = 5, phrase_time_limit: int | None = None) -> str:
    result = transcribe_microphone(timeout=timeout, phrase_time_limit=phrase_time_limit)
    if not result.get("success"):
        return ""
    return str(result.get("text", "")).strip()
