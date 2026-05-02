from __future__ import annotations

import threading
import time
from typing import Any, Dict, Optional

from voice.mic_handler import get_microphone_status
from voice.speech_to_text import get_stt_status, transcribe_microphone
from voice.voice_config import load_voice_settings
from voice.wake_word import detect_wake_word

try:
    import pyttsx3  # type: ignore
except Exception:  # pragma: no cover
    pyttsx3 = None


WAKE_PHRASE = "hey aura"
UNAVAILABLE_MESSAGE = "Desktop voice runtime is not available on this system."
INACTIVE_MESSAGE = "Desktop voice runtime is not active."

_LOCK = threading.RLock()
_STOP_EVENT = threading.Event()
_INTERRUPT_EVENT = threading.Event()
_THREAD: Optional[threading.Thread] = None
_TTS_ENGINE: Any = None

_STATE: Dict[str, Any] = {
    "available": False,
    "active": False,
    "listening": False,
    "awake": False,
    "processing": False,
    "speaking": False,
    "last_error": "",
    "mode": "desktop_voice",
    "status": "inactive",
    "state": "off",
    "message": INACTIVE_MESSAGE,
    "wake_phrase": WAKE_PHRASE,
    "last_transcript": "",
    "last_command": "",
    "last_response": "",
    "last_spoken_text": "",
    "last_updated": time.time(),
}


def _dependency_snapshot() -> Dict[str, Any]:
    stt = get_stt_status()
    microphone = get_microphone_status()
    desktop_tts_available = pyttsx3 is not None
    available = bool(stt.get("available") and stt.get("supports_microphone") and microphone.get("available"))
    missing = []
    if not stt.get("available") or not stt.get("supports_microphone"):
        missing.append("speech_recognition")
    if not microphone.get("available"):
        missing.append("microphone")
    return {
        "available": available,
        "stt": stt,
        "microphone": microphone,
        "tts": {
            "available": desktop_tts_available,
            "backend": "pyttsx3" if desktop_tts_available else "unavailable",
        },
        "missing": missing,
    }


def _derive_state(payload: Dict[str, Any]) -> str:
    if not payload.get("active"):
        return "off"
    if payload.get("speaking"):
        return "speaking"
    if payload.get("processing"):
        return "processing"
    if payload.get("awake"):
        return "awake"
    if payload.get("listening"):
        return "listening"
    return "idle"


def _message_for_state(payload: Dict[str, Any]) -> str:
    if not payload.get("available"):
        return UNAVAILABLE_MESSAGE
    if not payload.get("active"):
        return INACTIVE_MESSAGE
    state = _derive_state(payload)
    if state == "listening":
        return 'Listening for "Hey AURA".'
    if state == "awake":
        return "Wake phrase detected. Waiting for the command."
    if state == "processing":
        return "Processing the desktop voice command."
    if state == "speaking":
        return "Speaking the response."
    return "Desktop voice runtime is active."


def _set_state(**updates: Any) -> Dict[str, Any]:
    with _LOCK:
        _STATE.update(updates)
        _STATE["state"] = _derive_state(_STATE)
        _STATE["status"] = _STATE["state"]
        _STATE["message"] = _message_for_state(_STATE)
        _STATE["last_updated"] = time.time()
        return dict(_STATE)


def _status_payload() -> Dict[str, Any]:
    dependencies = _dependency_snapshot()
    with _LOCK:
        payload = dict(_STATE)
        payload["available"] = bool(dependencies.get("available"))
        payload["dependencies"] = dependencies
        payload["message"] = _message_for_state(payload)
        payload["state"] = _derive_state(payload)
        payload["status"] = payload["state"]
        payload["wake_phrase"] = WAKE_PHRASE
        payload["mode"] = "desktop_voice"
        return payload


def get_desktop_voice_status() -> Dict[str, Any]:
    return _status_payload()


def start_desktop_voice(
    *,
    session_id: str = "default",
    user_profile: Optional[dict[str, Any]] = None,
    start_loop: bool = True,
) -> Dict[str, Any]:
    dependencies = _dependency_snapshot()
    if not dependencies.get("available"):
        status = _set_state(
            available=False,
            active=False,
            listening=False,
            awake=False,
            processing=False,
            speaking=False,
            last_error=UNAVAILABLE_MESSAGE,
        )
        status["success"] = False
        status["dependencies"] = dependencies
        return status

    global _THREAD
    with _LOCK:
        if _STATE.get("active"):
            status = _status_payload()
            status["success"] = True
            status["message"] = 'Desktop voice is already listening for "Hey AURA".'
            return status

        _STOP_EVENT.clear()
        _INTERRUPT_EVENT.clear()
        _set_state(
            available=True,
            active=True,
            listening=True,
            awake=False,
            processing=False,
            speaking=False,
            last_error="",
            last_transcript="",
            last_command="",
            last_response="",
            last_spoken_text="",
        )
        if start_loop:
            _THREAD = threading.Thread(
                target=_desktop_voice_loop,
                kwargs={"session_id": session_id, "user_profile": dict(user_profile or {})},
                name="AURA Desktop Voice Runtime",
                daemon=True,
            )
            _THREAD.start()
        else:
            _THREAD = None

    status = _status_payload()
    status["success"] = True
    status["message"] = 'Desktop voice runtime started. Listening for "Hey AURA".'
    return status


def stop_desktop_voice() -> Dict[str, Any]:
    global _THREAD
    _STOP_EVENT.set()
    _INTERRUPT_EVENT.set()
    _stop_desktop_tts()
    thread = _THREAD
    if thread and thread.is_alive() and thread is not threading.current_thread():
        thread.join(timeout=1.0)
    _THREAD = None
    status = _set_state(
        active=False,
        listening=False,
        awake=False,
        processing=False,
        speaking=False,
        last_error="",
    )
    status["success"] = True
    status["message"] = "Desktop voice runtime stopped."
    return status


def interrupt_desktop_voice() -> Dict[str, Any]:
    _INTERRUPT_EVENT.set()
    _stop_desktop_tts()
    with _LOCK:
        active = bool(_STATE.get("active"))
    status = _set_state(
        listening=active,
        awake=False,
        processing=False,
        speaking=False,
        last_error="",
    )
    status["success"] = True
    status["message"] = "Desktop voice runtime interrupted."
    return status


def _desktop_voice_loop(*, session_id: str, user_profile: dict[str, Any]) -> None:
    settings = load_voice_settings()
    while not _STOP_EVENT.is_set():
        _INTERRUPT_EVENT.clear()
        _set_state(listening=True, awake=False, processing=False, speaking=False)
        wake_result = _listen_once(timeout=4, phrase_time_limit=4)
        if _STOP_EVENT.is_set():
            break
        if not wake_result.get("success"):
            _handle_listen_failure(wake_result)
            continue

        transcript = str(wake_result.get("text") or "").strip()
        if not transcript:
            continue
        _set_state(last_transcript=transcript)
        wake = detect_wake_word(transcript, [WAKE_PHRASE])
        if not wake.get("detected"):
            continue

        command_text = str(wake.get("remaining_text") or "").strip()
        _set_state(listening=False, awake=True)
        if not command_text:
            command_result = _listen_once(timeout=6, phrase_time_limit=settings.phrase_time_limit)
            if _STOP_EVENT.is_set():
                break
            if not command_result.get("success"):
                _handle_listen_failure(command_result)
                continue
            command_text = str(command_result.get("text") or "").strip()
        if not command_text:
            _set_state(listening=True, awake=False)
            continue

        process_desktop_voice_command(command_text, session_id=session_id, user_profile=user_profile, speak=True)

    _set_state(active=False, listening=False, awake=False, processing=False, speaking=False)


def _listen_once(*, timeout: int, phrase_time_limit: int) -> Dict[str, Any]:
    return transcribe_microphone(timeout=timeout, phrase_time_limit=phrase_time_limit)


def _handle_listen_failure(result: Dict[str, Any]) -> None:
    message = str(result.get("message") or "").strip()
    lower = message.lower()
    expected_timeout = "timed out" in lower or "timeout" in lower or "phrase" in lower
    if expected_timeout:
        _set_state(last_error="")
        return
    _set_state(last_error=message or "Desktop voice transcription failed.")


def _run_runtime_command(command_text: str, *, session_id: str, user_profile: Optional[dict[str, Any]]) -> Dict[str, Any]:
    from brain.core_ai import process_command_detailed

    return process_command_detailed(
        command_text,
        session_id=session_id,
        user_profile=dict(user_profile or {}),
        current_mode="real",
    )


def process_desktop_voice_command(
    command_text: str,
    *,
    session_id: str = "default",
    user_profile: Optional[dict[str, Any]] = None,
    speak: bool = True,
) -> Dict[str, Any]:
    command = str(command_text or "").strip()
    if not command:
        return {"success": False, "status": "empty_command", "message": "No desktop voice command was captured."}

    _set_state(listening=False, awake=False, processing=True, speaking=False, last_command=command, last_error="")
    try:
        result = _run_runtime_command(command, session_id=session_id, user_profile=user_profile)
    except Exception as error:
        error_message = str(error)
        _set_state(processing=False, last_error=error_message)
        return {"success": False, "status": "runtime_error", "message": error_message, "command_text": command}

    response_text = str(result.get("response") or result.get("reply") or result.get("content") or "").strip()
    spoken_text = _safe_spoken_text(result, response_text)
    speech_result = {"success": False, "status": "skipped", "message": "Speech skipped."}
    _set_state(processing=False, last_response=response_text, last_spoken_text=spoken_text)
    if speak and spoken_text and not _STOP_EVENT.is_set() and not _INTERRUPT_EVENT.is_set():
        speech_result = speak_desktop_text(spoken_text)
    if not _STOP_EVENT.is_set():
        _set_state(listening=bool(_STATE.get("active")), awake=False, processing=False, speaking=False)
    return {
        "success": True,
        "status": "processed",
        "command_text": command,
        "response": response_text,
        "spoken_text": spoken_text,
        "speech": speech_result,
        "result": result,
    }


def _extract_result_trust_level(result: Dict[str, Any]) -> str:
    permission = result.get("permission") if isinstance(result, dict) else {}
    permission_info = permission.get("permission") if isinstance(permission, dict) else {}
    trust_level = str(permission_info.get("trust_level") or "").strip().lower()
    if trust_level:
        return trust_level
    if result.get("automation_confirmation_required"):
        return "sensitive"
    steps = result.get("action_steps") or (result.get("action_plan") or {}).get("steps") or []
    for step in steps if isinstance(steps, list) else []:
        action_type = str(step.get("action_type") or "").strip()
        if action_type == "automation_critical_blocked":
            return "critical"
        params = step.get("params") if isinstance(step, dict) else {}
        step_level = str((params or {}).get("trust_level") or "").strip().lower()
        if step_level in {"critical", "sensitive", "private"}:
            return step_level
    return "safe"


def _safe_spoken_text(result: Dict[str, Any], response_text: str) -> str:
    trust_level = _extract_result_trust_level(result)
    if trust_level == "critical":
        return "I blocked that action for safety."
    if trust_level in {"sensitive", "private"} or result.get("automation_confirmation_required"):
        return "This needs your approval in AURA before I can continue."
    return response_text[:1200]


def speak_desktop_text(text: str) -> Dict[str, Any]:
    clean_text = str(text or "").strip()
    if not clean_text:
        return {"success": False, "status": "empty_text", "message": "Speech text is empty."}
    if pyttsx3 is None:
        return {
            "success": False,
            "status": "unavailable",
            "message": "Desktop TTS is not available on this system.",
            "backend": "pyttsx3",
        }

    global _TTS_ENGINE
    try:
        _set_state(speaking=True, processing=False)
        engine = pyttsx3.init()
        with _LOCK:
            _TTS_ENGINE = engine
        engine.say(clean_text)
        engine.runAndWait()
        return {"success": True, "status": "spoken", "message": "Desktop voice response spoken.", "backend": "pyttsx3"}
    except Exception as error:
        _set_state(last_error=str(error))
        return {"success": False, "status": "tts_error", "message": str(error), "backend": "pyttsx3"}
    finally:
        with _LOCK:
            _TTS_ENGINE = None
        _set_state(speaking=False)


def _stop_desktop_tts() -> None:
    with _LOCK:
        engine = _TTS_ENGINE
    if engine is None:
        return
    try:
        engine.stop()
    except Exception:
        pass
