from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from voice.speech_to_text import stt_available

try:
    import speech_recognition as sr  # type: ignore
except Exception:  # pragma: no cover
    sr = None


def list_microphones() -> List[str]:
    if sr is None:
        return []
    try:
        return list(sr.Microphone.list_microphone_names())
    except Exception:
        return []


def get_microphone_status() -> Dict[str, Any]:
    names = list_microphones()
    return {
        "available": stt_available() and bool(names),
        "count": len(names),
        "devices": names[:8],
    }


def capture_microphone_audio(*, timeout: int = 5, phrase_time_limit: int = 8, save_path: str | None = None) -> Dict[str, Any]:
    if sr is None:
        return {"success": False, "status": "unavailable", "message": "Microphone capture backend is unavailable."}

    recognizer = sr.Recognizer()
    try:
        with sr.Microphone() as source:
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
        if save_path:
            path = Path(save_path).expanduser().resolve()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(audio.get_wav_data())
            return {"success": True, "status": "captured", "path": str(path)}
        return {"success": True, "status": "captured", "audio_bytes": len(audio.get_wav_data())}
    except Exception as error:
        return {"success": False, "status": "capture_error", "message": str(error)}
