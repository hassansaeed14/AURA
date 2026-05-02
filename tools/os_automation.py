from __future__ import annotations

import time
from typing import Any, Dict, Iterable, Optional

from tools.desktop_controller import get_application_label, normalize_application_name
from tools.screen_capture import screen_context_for_automation


SUPPORTED_AUTOMATION_APPS = {"chrome", "notepad", "calculator", "vs code"}
SENSITIVE_WINDOW_KEYWORDS = (
    "bank",
    "banking",
    "payment",
    "checkout",
    "paypal",
    "stripe",
    "password",
    "login",
    "log in",
    "sign in",
    "email compose",
    "compose",
    "new message",
)
CRITICAL_TEXT_KEYWORDS = (
    "password",
    "passcode",
    "otp",
    "pin",
    "credit card",
    "debit card",
    "bank account",
    "bank",
    "payment",
    "purchase",
    "checkout",
    "login",
    "credentials",
    "delete file",
    "delete all",
    "rm -rf",
    "format disk",
)
ALLOWED_KEYS = {
    "enter",
    "tab",
    "esc",
    "escape",
    "space",
    "backspace",
    "up",
    "down",
    "left",
    "right",
    "home",
    "end",
    "pageup",
    "pagedown",
}
ALLOWED_HOTKEYS = {
    ("ctrl", "a"),
    ("ctrl", "c"),
    ("ctrl", "v"),
    ("ctrl", "x"),
    ("ctrl", "z"),
    ("ctrl", "y"),
    ("ctrl", "l"),
    ("ctrl", "f"),
    ("ctrl", "n"),
    ("ctrl", "t"),
    ("ctrl", "w"),
}
MAX_TYPE_CHARS = 1000
TYPE_CHUNK_SIZE = 24
MAX_SCROLL_AMOUNT = 8
CONTROL_COOLDOWN_SECONDS = 0.08

_STOP_REQUESTED = False


def _log_action(name: str, status: str, detail: str | None = None) -> None:
    suffix = f" ({detail})" if detail else ""
    print(f"[OS ACTION] {name} -> {status}{suffix}")


def _log_blocked(reason: str, detail: str | None = None) -> None:
    suffix = f" ({detail})" if detail else ""
    print(f"[OS BLOCKED] {reason}{suffix}")


def _log_stopped(detail: str | None = None) -> None:
    suffix = f" ({detail})" if detail else ""
    print(f"[OS STOPPED] user interrupt{suffix}")


def _automation_result(
    *,
    success: bool,
    status: str,
    message: str,
    target_app: str | None = None,
    active_window: str | None = None,
    error: str | None = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "success": bool(success),
        "status": status,
        "message": message,
        "target_app": target_app,
        "active_window": active_window,
        "trust_level": "sensitive" if status not in {"focused", "unsupported"} else "safe",
    }
    if error:
        payload["error"] = error
    if extra:
        payload.update(extra)
    return payload


def request_stop() -> Dict[str, Any]:
    global _STOP_REQUESTED
    _STOP_REQUESTED = True
    _log_stopped("stop flag set")
    return {"success": True, "status": "stop_requested", "message": "Control stop requested."}


def reset_stop_flag() -> None:
    global _STOP_REQUESTED
    _STOP_REQUESTED = False


def is_stop_requested() -> bool:
    return bool(_STOP_REQUESTED)


def _pyautogui():
    try:
        import pyautogui as module  # type: ignore
    except Exception as error:  # pragma: no cover - environment-dependent
        raise RuntimeError("pyautogui is not available in this environment.") from error
    module.FAILSAFE = True
    module.PAUSE = min(float(getattr(module, "PAUSE", 0.05) or 0.05), 0.1)
    return module


def _normalize_app(app_name: str | None) -> Optional[str]:
    normalized = normalize_application_name(app_name)
    if normalized in SUPPORTED_AUTOMATION_APPS:
        return normalized
    return None


def _title_matches_app(title: str, app_name: str) -> bool:
    lowered = str(title or "").lower()
    if app_name == "chrome":
        return "chrome" in lowered
    if app_name == "notepad":
        return "notepad" in lowered
    if app_name == "calculator":
        return "calculator" in lowered or "calc" in lowered
    if app_name == "vs code":
        return "visual studio code" in lowered or " vs code" in lowered or lowered.endswith("code")
    return False


def appears_sensitive_window(title: str | None) -> bool:
    lowered = str(title or "").strip().lower()
    return bool(lowered and any(keyword in lowered for keyword in SENSITIVE_WINDOW_KEYWORDS))


def appears_critical_text(text: str | None) -> bool:
    lowered = str(text or "").strip().lower()
    return bool(lowered and any(keyword in lowered for keyword in CRITICAL_TEXT_KEYWORDS))


def get_active_window_title() -> str:
    try:
        active = _pyautogui().getActiveWindow()
    except RuntimeError:
        return ""
    title = getattr(active, "title", "") if active else ""
    return str(title or "").strip()


def _validate_target_app(target_app: str | None) -> Dict[str, Any]:
    normalized = _normalize_app(target_app)
    if not normalized:
        _log_blocked("unsupported app", str(target_app or "").strip() or "unknown")
        return _automation_result(
            success=False,
            status="unsupported",
            message="I can only automate Chrome, Notepad, Calculator, or VS Code.",
            target_app=str(target_app or "").strip() or None,
            error="Unsupported automation target.",
        )
    return {"success": True, "app_name": normalized, "label": get_application_label(normalized) or normalized.title()}


def _validate_active_window(target_app: str | None) -> Dict[str, Any]:
    app = _validate_target_app(target_app)
    if not app.get("success"):
        return app

    normalized = str(app["app_name"])
    title = get_active_window_title()
    if appears_sensitive_window(title):
        _log_blocked("sensitive window", title)
        return _automation_result(
            success=False,
            status="sensitive_window_blocked",
            message="I stopped because the active window appears sensitive.",
            target_app=normalized,
            active_window=title,
            error="Sensitive active window.",
        )
    if not title or not _title_matches_app(title, normalized):
        _log_blocked("wrong active window", f"target={normalized}; active={title or 'none'}")
        return _automation_result(
            success=False,
            status="wrong_active_window",
            message=f"I need {app['label']} to be the active window before controlling it.",
            target_app=normalized,
            active_window=title,
            error="Active window did not match target app.",
        )
    return {"success": True, "app_name": normalized, "label": app["label"], "active_window": title}


def focus_supported_app(app_name: str | None) -> Dict[str, Any]:
    app = _validate_target_app(app_name)
    if not app.get("success"):
        return app
    normalized = str(app["app_name"])
    label = str(app["label"])
    try:
        module = _pyautogui()
        windows = list(module.getWindowsWithTitle(label) or [])
        if not windows and normalized == "vs code":
            windows = list(module.getWindowsWithTitle("Visual Studio Code") or [])
        if not windows and normalized == "chrome":
            windows = list(module.getWindowsWithTitle("Chrome") or [])
        if not windows:
            _log_blocked("window not found", label)
            return _automation_result(
                success=False,
                status="window_not_found",
                message=f"I couldn't find an active {label} window to focus.",
                target_app=normalized,
                error="No matching window.",
            )
        window = windows[0]
        title = str(getattr(window, "title", "") or "")
        if appears_sensitive_window(title):
            _log_blocked("sensitive window", title)
            return _automation_result(
                success=False,
                status="sensitive_window_blocked",
                message="I stopped because the matching window appears sensitive.",
                target_app=normalized,
                active_window=title,
                error="Sensitive window.",
            )
        window.activate()
        _log_action("focus_supported_app", "success", normalized)
        return _automation_result(
            success=True,
            status="focused",
            message=f"Focused {label}.",
            target_app=normalized,
            active_window=title,
        )
    except RuntimeError as error:
        return _automation_result(
            success=False,
            status="unavailable",
            message=str(error),
            target_app=normalized,
            error=str(error),
        )
    except Exception as error:  # pragma: no cover - pyautogui backend dependent
        return _automation_result(
            success=False,
            status="focus_failed",
            message=f"I couldn't focus {label}: {error}",
            target_app=normalized,
            error=str(error),
        )


def _screen_observation_check(target_app: str | None, action_type: str) -> Dict[str, Any]:
    context = screen_context_for_automation(target_app, action_type)
    if context.get("sensitive_detected"):
        _log_blocked("sensitive screen", str(context.get("visible_text") or "")[:80])
        return _automation_result(
            success=False,
            status="sensitive_screen_blocked",
            message="I stopped because the visible screen appears sensitive.",
            target_app=str(target_app or "").strip() or None,
            error="Sensitive screen text detected.",
            extra={"screen_context": context},
        )
    return {"success": True, "screen_context": context}


def _pre_control_check(target_app: str | None, *, text: str | None = None, action_type: str = "control") -> Dict[str, Any]:
    if is_stop_requested():
        _log_stopped("before control action")
        return _automation_result(
            success=False,
            status="stopped",
            message="Control is stopped.",
            target_app=str(target_app or "").strip() or None,
            error="Emergency stop requested.",
        )
    if appears_critical_text(text):
        _log_blocked("sensitive content", str(text or "")[:60])
        return _automation_result(
            success=False,
            status="critical_blocked",
            message="I can't automate passwords, payments, banking, destructive actions, or sensitive account text.",
            target_app=str(target_app or "").strip() or None,
            error="Critical automation content blocked.",
            extra={"trust_level": "critical"},
        )
    active = _validate_active_window(target_app)
    if not active.get("success"):
        return active
    screen = _screen_observation_check(str(active.get("app_name") or target_app or ""), action_type)
    if not screen.get("success"):
        return screen
    active["screen_context"] = screen.get("screen_context")
    return active


def _control_cooldown() -> None:
    time.sleep(CONTROL_COOLDOWN_SECONDS)


def _stopped_result(action_name: str, target_app: str | None, active_window: str | None = None) -> Dict[str, Any]:
    _log_stopped(action_name)
    return _automation_result(
        success=False,
        status="stopped",
        message="Control stopped before the action could continue.",
        target_app=str(target_app or "").strip() or None,
        active_window=active_window,
        error="Emergency stop requested.",
    )


def type_text(text: str | None, target_app: str | None) -> Dict[str, Any]:
    safe_text = str(text or "").replace("\x00", " ")[:MAX_TYPE_CHARS]
    if not safe_text:
        return _automation_result(
            success=False,
            status="invalid_text",
            message="I need text before I can type into an app.",
            target_app=str(target_app or "").strip() or None,
            error="Missing text.",
        )
    check = _pre_control_check(target_app, text=safe_text, action_type="type_text")
    if not check.get("success"):
        return check
    try:
        module = _pyautogui()
        for start in range(0, len(safe_text), TYPE_CHUNK_SIZE):
            if is_stop_requested():
                return _stopped_result("type_text", str(check["app_name"]), str(check["active_window"]))
            chunk = safe_text[start : start + TYPE_CHUNK_SIZE]
            module.write(chunk, interval=0)
            if is_stop_requested():
                return _stopped_result("type_text", str(check["app_name"]), str(check["active_window"]))
            if start + TYPE_CHUNK_SIZE < len(safe_text):
                _control_cooldown()
        _log_action("type_text", "success", f"{len(safe_text)} chars")
        return _automation_result(
            success=True,
            status="typed",
            message=f"Typed text into {check['label']}.",
            target_app=str(check["app_name"]),
            active_window=str(check["active_window"]),
            extra={"chars": len(safe_text), "screen_context": check.get("screen_context")},
        )
    except Exception as error:  # pragma: no cover - pyautogui backend dependent
        return _automation_result(
            success=False,
            status="type_failed",
            message=f"I couldn't type into {check['label']}: {error}",
            target_app=str(check["app_name"]),
            active_window=str(check["active_window"]),
            error=str(error),
        )


def press_key(key: str | None, target_app: str | None) -> Dict[str, Any]:
    normalized_key = str(key or "").strip().lower()
    if normalized_key not in ALLOWED_KEYS:
        return _automation_result(
            success=False,
            status="unsupported_key",
            message="I can only press a small safe allowlist of keys.",
            target_app=str(target_app or "").strip() or None,
            error="Unsupported key.",
        )
    check = _pre_control_check(target_app, action_type="press_key")
    if not check.get("success"):
        return check
    if is_stop_requested():
        return _stopped_result("press_key", str(check["app_name"]), str(check["active_window"]))
    _pyautogui().press(normalized_key)
    _log_action("press_key", "success", normalized_key)
    return _automation_result(
        success=True,
        status="key_pressed",
        message=f"Pressed {normalized_key} in {check['label']}.",
        target_app=str(check["app_name"]),
        active_window=str(check["active_window"]),
        extra={"key": normalized_key, "screen_context": check.get("screen_context")},
    )


def hotkey(keys: Iterable[str] | None, target_app: str | None) -> Dict[str, Any]:
    normalized_keys = tuple(str(key or "").strip().lower() for key in (keys or ()) if str(key or "").strip())
    if normalized_keys not in ALLOWED_HOTKEYS:
        return _automation_result(
            success=False,
            status="unsupported_hotkey",
            message="I can only use a small safe allowlist of hotkeys.",
            target_app=str(target_app or "").strip() or None,
            error="Unsupported hotkey.",
        )
    check = _pre_control_check(target_app, action_type="hotkey")
    if not check.get("success"):
        return check
    if is_stop_requested():
        return _stopped_result("hotkey", str(check["app_name"]), str(check["active_window"]))
    _pyautogui().hotkey(*normalized_keys)
    _log_action("hotkey", "success", "+".join(normalized_keys))
    return _automation_result(
        success=True,
        status="hotkey_pressed",
        message=f"Pressed {'+'.join(normalized_keys)} in {check['label']}.",
        target_app=str(check["app_name"]),
        active_window=str(check["active_window"]),
        extra={"keys": list(normalized_keys), "screen_context": check.get("screen_context")},
    )


def scroll(amount: int | str | None, target_app: str | None) -> Dict[str, Any]:
    try:
        parsed = int(amount or 0)
    except (TypeError, ValueError):
        parsed = 0
    parsed = max(-MAX_SCROLL_AMOUNT, min(MAX_SCROLL_AMOUNT, parsed))
    if parsed == 0:
        return _automation_result(
            success=False,
            status="invalid_scroll",
            message="I need a scroll direction or amount.",
            target_app=str(target_app or "").strip() or None,
            error="Missing scroll amount.",
        )
    check = _pre_control_check(target_app, action_type="scroll")
    if not check.get("success"):
        return check
    if is_stop_requested():
        return _stopped_result("scroll", str(check["app_name"]), str(check["active_window"]))
    _pyautogui().scroll(parsed)
    _log_action("scroll", "success", str(parsed))
    return _automation_result(
        success=True,
        status="scrolled",
        message=f"Scrolled {check['label']}.",
        target_app=str(check["app_name"]),
        active_window=str(check["active_window"]),
        extra={"amount": parsed, "screen_context": check.get("screen_context")},
    )


__all__ = [
    "appears_critical_text",
    "appears_sensitive_window",
    "focus_supported_app",
    "get_active_window_title",
    "hotkey",
    "is_stop_requested",
    "press_key",
    "request_stop",
    "reset_stop_flag",
    "scroll",
    "type_text",
]
