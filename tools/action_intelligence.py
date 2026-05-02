from __future__ import annotations

import hashlib
import re
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from brain.command_splitter import split_commands
from tools.action_memory import get_action_suggestions, record_action_plan
from tools.browser_actions import navigate_to_url, open_new_tab, open_search_result, open_url, rerun_search, search_query
from tools.desktop_controller import (
    get_application_label,
    normalize_application_name,
    open_application,
)
from tools.os_automation import (
    appears_critical_text,
    focus_supported_app,
    hotkey,
    press_key,
    reset_stop_flag,
    scroll,
    type_text,
)


OPEN_ACTION_RE = re.compile(
    r"^(?:please\s+)?(?:open|launch|start)\s+(?:the\s+)?(?P<target>[a-z0-9 .-]+?)(?:\s+(?:app|application|browser))?[.!?]*$",
    flags=re.IGNORECASE,
)
THIRD_PARTY_ASK_ACTION_RE = re.compile(
    r"^(?:please\s+)?(?:ask|tell)\s+(?:it|chatgpt|the\s+(?:site|page|website))\s+to\s+(?P<text>.+?)\s*[.!?]*$",
    flags=re.IGNORECASE,
)
SEARCH_ACTION_RE = re.compile(
    r"^(?:please\s+)?(?:(?:search|google|look\s+up|find)\s+(?:for\s+)?|search\s+the\s+web\s+for\s+)(?P<query>.+?)\s*[.!?]*$",
    flags=re.IGNORECASE,
)
URL_ACTION_RE = re.compile(
    r"^(?:please\s+)?(?:(?:go|navigate)\s+to|visit|open)\s+(?:the\s+)?(?P<target>(?:https?://)?[a-z0-9][a-z0-9.-]+\.[a-z]{2,}(?:/[^\s]*)?)\s*[.!?]*$",
    flags=re.IGNORECASE,
)
RESULT_ACTION_RE = re.compile(
    r"^(?:please\s+)?(?:open|launch|go\s+to)\s+(?:the\s+)?(?P<rank>first|top|next)\s+(?:search\s+)?(?:result|link)(?:\s+(?:for|on)\s+(?P<query>.+?))?\s*[.!?]*$",
    flags=re.IGNORECASE,
)
NEW_TAB_ACTION_RE = re.compile(
    r"^(?:please\s+)?(?:open|launch|start)\s+(?:a\s+)?(?:new\s+)?(?:browser\s+)?tab\s*[.!?]*$",
    flags=re.IGNORECASE,
)
RERUN_SEARCH_ACTION_RE = re.compile(
    r"^(?:please\s+)?(?:re[-\s]?run|repeat)\s+(?:the\s+)?search(?:\s+(?:for\s+)?(?P<query>.+?))?\s*[.!?]*$",
    flags=re.IGNORECASE,
)
TYPE_ACTION_RE = re.compile(
    r"^(?:please\s+)?(?:type|write|enter)\s+(?P<text>.+?)(?:\s+(?:in|into)\s+(?P<app>chrome|google chrome|notepad|calculator|calc|vs\s*code|vscode|visual studio code))?\s*[.!?]*$",
    flags=re.IGNORECASE,
)
FOCUS_ACTION_RE = re.compile(
    r"^(?:please\s+)?(?:focus|switch\s+to)\s+(?:the\s+)?(?P<app>chrome|google chrome|notepad|calculator|calc|vs\s*code|vscode|visual studio code)(?:\s+window)?\s*[.!?]*$",
    flags=re.IGNORECASE,
)
PRESS_KEY_ACTION_RE = re.compile(
    r"^(?:please\s+)?(?:press|hit)\s+(?P<key>enter|tab|escape|esc|space|backspace|up|down|left|right|home|end|pageup|pagedown)(?:\s+(?:in|inside)\s+(?P<app>chrome|google chrome|notepad|calculator|calc|vs\s*code|vscode|visual studio code))?\s*[.!?]*$",
    flags=re.IGNORECASE,
)
HOTKEY_ACTION_RE = re.compile(
    r"^(?:please\s+)?(?:press|use|hit)\s+(?P<modifier>ctrl|control)\s*\+?\s*(?P<key>[a-z])(?:\s+(?:in|inside)\s+(?P<app>chrome|google chrome|notepad|calculator|calc|vs\s*code|vscode|visual studio code))?\s*[.!?]*$",
    flags=re.IGNORECASE,
)
SCROLL_ACTION_RE = re.compile(
    r"^(?:please\s+)?scroll\s+(?P<direction>up|down)(?:\s+(?:in|inside)\s+(?P<app>chrome|google chrome|notepad|calculator|calc|vs\s*code|vscode|visual studio code))?\s*[.!?]*$",
    flags=re.IGNORECASE,
)
CRITICAL_AUTOMATION_RE = re.compile(
    r"\b(delete|remove|wipe|format|purchase|buy|pay|payment|checkout|password|bank|banking|otp|pin|credential|credentials|credit\s+card|debit\s+card)\b",
    flags=re.IGNORECASE,
)
SAFE_WEB_TARGETS = {
    "youtube": ("YouTube", "https://www.youtube.com/"),
    "google": ("Google", "https://www.google.com/"),
    "chatgpt": ("ChatGPT", "https://chatgpt.com/"),
    "facebook": ("Facebook", "https://www.facebook.com/"),
    "github": ("GitHub", "https://github.com/"),
}
SAFE_ACTION_TYPES = {
    "desktop_open",
    "browser_search",
    "browser_open_url",
    "browser_navigate_url",
    "browser_open_result",
    "browser_new_tab",
    "browser_rerun_search",
    "automation_confirm",
    "automation_focus",
    "automation_type",
    "automation_press_key",
    "automation_hotkey",
    "automation_scroll",
    "automation_critical_blocked",
}
CONTROL_ACTION_TYPES = {"automation_type", "automation_press_key", "automation_hotkey", "automation_scroll"}
AUTOMATION_ACTION_TYPES = CONTROL_ACTION_TYPES | {"automation_focus", "automation_confirm"}
ACTION_STEP_COOLDOWN_SECONDS = 0.08


def classify_external_command_safety(command: str) -> Dict[str, str]:
    """Classify external/action-style free text without over-blocking searches."""

    text = str(command or "").strip().lower()
    if not text:
        return {"trust_level": "safe", "action_name": "general", "reason": "empty command"}
    if CRITICAL_AUTOMATION_RE.search(text):
        return {
            "trust_level": "critical",
            "action_name": "os_automation_critical",
            "reason": "critical terms such as passwords, payments, banking, credentials, or deletion are blocked",
        }
    if re.search(r"\b(?:type|write|enter|ask|tell)\b", text):
        return {
            "trust_level": "sensitive",
            "action_name": "os_automation_control",
            "reason": "the request may type user-provided text into an app or website",
        }
    if re.search(r"\b(?:open|launch|go to|visit|navigate|search|google|look up|find)\b", text):
        return {
            "trust_level": "safe",
            "action_name": "desktop_launch",
            "reason": "safe whitelisted app, URL, or search navigation",
        }
    return {"trust_level": "safe", "action_name": "general", "reason": "no controlled action detected"}


@dataclass
class ActionStep:
    step_id: str
    action_type: str
    target: str
    label: str
    source_text: str
    params: Dict[str, Any] = field(default_factory=dict)
    status: str = "pending"
    message: str = ""
    result: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ActionPlan:
    plan_id: str
    original_command: str
    steps: List[ActionStep]
    status: str = "planned"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "original_command": self.original_command,
            "status": self.status,
            "steps": [step.to_dict() for step in self.steps],
        }


def _plan_id(command: str) -> str:
    digest = hashlib.sha1(str(command or "").encode("utf-8")).hexdigest()[:10]
    return f"action-{digest}"


def _clean_target(value: str, *, limit: int = 180) -> str:
    return " ".join(str(value or "").replace("\x00", " ").split())[:limit].strip()


def _parse_open_step(fragment: str, index: int) -> Optional[ActionStep]:
    match = OPEN_ACTION_RE.match(str(fragment or "").strip())
    if not match:
        return None
    raw_target = _clean_target(match.group("target")).lower()
    web_target = SAFE_WEB_TARGETS.get(raw_target)
    if web_target:
        label, url = web_target
        return ActionStep(
            step_id=f"step-{index}",
            action_type="browser_open_url",
            target=url,
            label=f"Open {label}",
            source_text=str(fragment or "").strip(),
        )

    app_name = normalize_application_name(match.group("target"))
    if not app_name:
        return None
    label = get_application_label(app_name) or app_name.title()
    return ActionStep(
        step_id=f"step-{index}",
        action_type="desktop_open",
        target=app_name,
        label=f"Open {label}",
        source_text=str(fragment or "").strip(),
    )


def _parse_third_party_ask_step(fragment: str, index: int) -> Optional[ActionStep]:
    match = THIRD_PARTY_ASK_ACTION_RE.match(str(fragment or "").strip())
    if not match:
        return None
    text = _clean_target(match.group("text"), limit=1000)
    if not text:
        return None
    if appears_critical_text(text) or CRITICAL_AUTOMATION_RE.search(text):
        return ActionStep(
            step_id=f"step-{index}",
            action_type="automation_critical_blocked",
            target="",
            label="Block critical automation",
            source_text=str(fragment or "").strip(),
            params={"reason": "critical_text", "trust_level": "critical"},
        )
    return ActionStep(
        step_id=f"step-{index}",
        action_type="automation_type",
        target="chrome",
        label="Type prompt into browser",
        source_text=str(fragment or "").strip(),
        params={"text": text, "trust_level": "sensitive", "requires_confirmation": True},
    )


def _parse_search_step(fragment: str, index: int) -> Optional[ActionStep]:
    match = SEARCH_ACTION_RE.match(str(fragment or "").strip())
    if not match:
        return None
    query = _clean_target(match.group("query"))
    if not query:
        return None
    return ActionStep(
        step_id=f"step-{index}",
        action_type="browser_search",
        target=query,
        label=f"Search for {query}",
        source_text=str(fragment or "").strip(),
    )


def _parse_new_tab_step(fragment: str, index: int) -> Optional[ActionStep]:
    match = NEW_TAB_ACTION_RE.match(str(fragment or "").strip())
    if not match:
        return None
    return ActionStep(
        step_id=f"step-{index}",
        action_type="browser_new_tab",
        target="",
        label="Open new Chrome tab",
        source_text=str(fragment or "").strip(),
    )


def _parse_rerun_search_step(fragment: str, index: int) -> Optional[ActionStep]:
    match = RERUN_SEARCH_ACTION_RE.match(str(fragment or "").strip())
    if not match:
        return None
    query = _clean_target(match.group("query") or "")
    return ActionStep(
        step_id=f"step-{index}",
        action_type="browser_rerun_search",
        target=query,
        label=f"Re-run search{f' for {query}' if query else ''}",
        source_text=str(fragment or "").strip(),
    )


def _normalize_app_target(value: str | None) -> str:
    return normalize_application_name(value) or ""


def _parse_focus_step(fragment: str, index: int) -> Optional[ActionStep]:
    match = FOCUS_ACTION_RE.match(str(fragment or "").strip())
    if not match:
        return None
    app_name = _normalize_app_target(match.group("app"))
    if not app_name:
        return None
    label = get_application_label(app_name) or app_name.title()
    return ActionStep(
        step_id=f"step-{index}",
        action_type="automation_focus",
        target=app_name,
        label=f"Focus {label}",
        source_text=str(fragment or "").strip(),
        params={"trust_level": "safe"},
    )


def _parse_critical_step(fragment: str, index: int) -> Optional[ActionStep]:
    text = str(fragment or "").strip()
    lowered = text.lower()
    if lowered.startswith(("search ", "google ", "look up ", "find ")):
        return None
    if not CRITICAL_AUTOMATION_RE.search(text):
        return None
    return ActionStep(
        step_id=f"step-{index}",
        action_type="automation_critical_blocked",
        target="",
        label="Block critical automation",
        source_text=text,
        params={"reason": "critical_action", "trust_level": "critical"},
    )


def _parse_type_step(fragment: str, index: int) -> Optional[ActionStep]:
    match = TYPE_ACTION_RE.match(str(fragment or "").strip())
    if not match:
        return None
    text = _clean_target(match.group("text"), limit=1000)
    if not text:
        return None
    if appears_critical_text(text):
        return ActionStep(
            step_id=f"step-{index}",
            action_type="automation_critical_blocked",
            target="",
            label="Block critical automation",
            source_text=str(fragment or "").strip(),
            params={"reason": "critical_text", "trust_level": "critical"},
        )
    app_name = _normalize_app_target(match.group("app") or "")
    return ActionStep(
        step_id=f"step-{index}",
        action_type="automation_type",
        target=app_name,
        label="Type text",
        source_text=str(fragment or "").strip(),
        params={"text": text, "trust_level": "sensitive", "requires_confirmation": True},
    )


def _parse_press_key_step(fragment: str, index: int) -> Optional[ActionStep]:
    match = PRESS_KEY_ACTION_RE.match(str(fragment or "").strip())
    if not match:
        return None
    app_name = _normalize_app_target(match.group("app") or "")
    key = _clean_target(match.group("key")).lower()
    return ActionStep(
        step_id=f"step-{index}",
        action_type="automation_press_key",
        target=app_name,
        label=f"Press {key}",
        source_text=str(fragment or "").strip(),
        params={"key": key, "trust_level": "sensitive", "requires_confirmation": True},
    )


def _parse_hotkey_step(fragment: str, index: int) -> Optional[ActionStep]:
    match = HOTKEY_ACTION_RE.match(str(fragment or "").strip())
    if not match:
        return None
    app_name = _normalize_app_target(match.group("app") or "")
    key = _clean_target(match.group("key")).lower()
    return ActionStep(
        step_id=f"step-{index}",
        action_type="automation_hotkey",
        target=app_name,
        label=f"Press Ctrl+{key.upper()}",
        source_text=str(fragment or "").strip(),
        params={"keys": ["ctrl", key], "trust_level": "sensitive", "requires_confirmation": True},
    )


def _parse_scroll_step(fragment: str, index: int) -> Optional[ActionStep]:
    match = SCROLL_ACTION_RE.match(str(fragment or "").strip())
    if not match:
        return None
    direction = str(match.group("direction") or "").lower()
    app_name = _normalize_app_target(match.group("app") or "")
    amount = -4 if direction == "down" else 4
    return ActionStep(
        step_id=f"step-{index}",
        action_type="automation_scroll",
        target=app_name,
        label=f"Scroll {direction}",
        source_text=str(fragment or "").strip(),
        params={"amount": amount, "trust_level": "sensitive", "requires_confirmation": True},
    )


def _parse_url_step(fragment: str, index: int) -> Optional[ActionStep]:
    match = URL_ACTION_RE.match(str(fragment or "").strip())
    if not match:
        return None
    target = _clean_target(match.group("target"))
    if not target:
        return None
    source_text = str(fragment or "").strip()
    action_type = "browser_navigate_url" if re.match(r"^(?:please\s+)?(?:(?:go|navigate)\s+to|visit)\b", source_text, flags=re.IGNORECASE) else "browser_open_url"
    verb = "Navigate to" if action_type == "browser_navigate_url" else "Open"
    return ActionStep(
        step_id=f"step-{index}",
        action_type=action_type,
        target=target,
        label=f"{verb} {target}",
        source_text=source_text,
    )


def _parse_result_step(fragment: str, index: int) -> Optional[ActionStep]:
    match = RESULT_ACTION_RE.match(str(fragment or "").strip())
    if not match:
        return None
    query = _clean_target(match.group("query") or "")
    rank = str(match.group("rank") or "top").lower()
    result_index = 2 if rank == "next" else 1
    label_rank = "next" if result_index > 1 else "top"
    return ActionStep(
        step_id=f"step-{index}",
        action_type="browser_open_result",
        target=query,
        label=f"Open {label_rank} result{f' for {query}' if query else ''}",
        source_text=str(fragment or "").strip(),
        params={"result_index": result_index},
    )


def parse_action_step(fragment: str, index: int) -> Optional[ActionStep]:
    return (
        _parse_new_tab_step(fragment, index)
        or _parse_rerun_search_step(fragment, index)
        or _parse_focus_step(fragment, index)
        or _parse_third_party_ask_step(fragment, index)
        or _parse_type_step(fragment, index)
        or _parse_critical_step(fragment, index)
        or _parse_press_key_step(fragment, index)
        or _parse_hotkey_step(fragment, index)
        or _parse_scroll_step(fragment, index)
        or _parse_url_step(fragment, index)
        or _parse_result_step(fragment, index)
        or _parse_open_step(fragment, index)
        or _parse_search_step(fragment, index)
    )


def _hydrate_result_steps(steps: List[ActionStep]) -> None:
    last_query = ""
    last_app = ""
    for step in steps:
        if step.action_type == "desktop_open" and step.target:
            last_app = step.target
        if step.action_type.startswith("browser_"):
            last_app = "chrome"
        if step.action_type in {"browser_search", "browser_rerun_search"} and step.target:
            last_query = step.target
        if step.action_type in {"browser_open_result", "browser_rerun_search"} and not step.target and last_query:
            step.target = last_query
            if step.action_type == "browser_open_result":
                rank = "next" if int(step.params.get("result_index", 1) or 1) > 1 else "top"
                step.label = f"Open {rank} result for {last_query}"
            else:
                step.label = f"Re-run search for {last_query}"
        if step.action_type in AUTOMATION_ACTION_TYPES and not step.target and last_app:
            step.target = last_app
            if step.action_type == "automation_focus":
                label = get_application_label(last_app) or last_app.title()
                step.label = f"Focus {label}"


def _insert_automation_confirmation(steps: List[ActionStep]) -> List[ActionStep]:
    if not any(step.action_type in CONTROL_ACTION_TYPES for step in steps):
        return steps
    updated: List[ActionStep] = []
    inserted = False
    for step in steps:
        if step.action_type in CONTROL_ACTION_TYPES and not inserted:
            updated.append(
                ActionStep(
                    step_id=f"step-{len(updated) + 1}",
                    action_type="automation_confirm",
                    target=step.target,
                    label="Confirm keyboard/mouse control",
                    source_text="confirmation required",
                    params={
                        "trust_level": "sensitive",
                        "requires_confirmation": True,
                        "prompt": "Do you want me to control your keyboard/mouse for this action?",
                    },
                )
            )
            inserted = True
        updated.append(step)
    for index, step in enumerate(updated, start=1):
        step.step_id = f"step-{index}"
    return updated


def build_action_plan(command: str) -> Optional[ActionPlan]:
    fragments = split_commands(command)
    if not fragments:
        return None

    steps: List[ActionStep] = []
    for index, fragment in enumerate(fragments, start=1):
        step = parse_action_step(fragment, index)
        if step is None or step.action_type not in SAFE_ACTION_TYPES:
            return None
        steps.append(step)

    _hydrate_result_steps(steps)
    steps = _insert_automation_confirmation(steps)
    allowed_single_steps = {
        "browser_new_tab",
        "browser_open_url",
        "browser_navigate_url",
        "browser_open_result",
        "browser_rerun_search",
        "automation_focus",
        "automation_critical_blocked",
    }
    if len(steps) < 2 and steps[0].action_type not in allowed_single_steps:
        return None
    return ActionPlan(plan_id=_plan_id(command), original_command=str(command or "").strip(), steps=steps)


def _running_message(step: ActionStep) -> str:
    if step.action_type == "desktop_open":
        return f"Opening {step.label.replace('Open ', '')}..."
    if step.action_type == "browser_search":
        return f"Searching for {step.target}..."
    if step.action_type == "browser_open_url":
        return f"Opening {step.target}..."
    if step.action_type == "browser_navigate_url":
        return f"Navigating to {step.target}..."
    if step.action_type == "browser_new_tab":
        return "Opening a new Chrome tab..."
    if step.action_type == "browser_rerun_search":
        return f"Re-running the search for {step.target}..." if step.target else "Re-running the search..."
    if step.action_type == "browser_open_result":
        rank = "next" if int(step.params.get("result_index", 1) or 1) > 1 else "top"
        return f"Opening the {rank} result for {step.target}..." if step.target else f"Opening the {rank} result..."
    if step.action_type == "automation_confirm":
        return "Do you want me to control your keyboard/mouse for this action?"
    if step.action_type == "automation_focus":
        label = get_application_label(step.target) or step.target.title()
        return f"Focusing {label}..."
    if step.action_type == "automation_type":
        label = get_application_label(step.target) or step.target.title()
        return f"Typing into {label}..."
    if step.action_type == "automation_press_key":
        return f"Pressing {step.params.get('key')}..."
    if step.action_type == "automation_hotkey":
        return f"Pressing {'+'.join(step.params.get('keys', []))}..."
    if step.action_type == "automation_scroll":
        return "Scrolling..."
    if step.action_type == "automation_critical_blocked":
        return "That automation request is blocked for safety."
    return f"Running {step.label}..."


def _execute_step(step: ActionStep, *, automation_confirmed: bool = False) -> Dict[str, Any]:
    if step.action_type == "desktop_open":
        return open_application(step.target)
    if step.action_type == "browser_search":
        return search_query(step.target)
    if step.action_type == "browser_open_url":
        return open_url(step.target)
    if step.action_type == "browser_navigate_url":
        return navigate_to_url(step.target)
    if step.action_type == "browser_new_tab":
        return open_new_tab()
    if step.action_type == "browser_rerun_search":
        return rerun_search(step.target)
    if step.action_type == "browser_open_result":
        return open_search_result(step.target, result_index=int(step.params.get("result_index", 1) or 1))
    if step.action_type == "automation_confirm":
        if automation_confirmed:
            return {
                "success": True,
                "status": "confirmed",
                "message": "Keyboard/mouse control approved for this action.",
                "trust_level": "sensitive",
            }
        return {
            "success": False,
            "status": "needs_confirmation",
            "message": "Do you want me to control your keyboard/mouse for this action?",
            "requires_confirmation": True,
            "trust_level": "sensitive",
        }
    if step.action_type == "automation_focus":
        return focus_supported_app(step.target)
    if step.action_type == "automation_type":
        return type_text(str(step.params.get("text") or ""), step.target)
    if step.action_type == "automation_press_key":
        return press_key(str(step.params.get("key") or ""), step.target)
    if step.action_type == "automation_hotkey":
        return hotkey(step.params.get("keys") or [], step.target)
    if step.action_type == "automation_scroll":
        return scroll(step.params.get("amount"), step.target)
    if step.action_type == "automation_critical_blocked":
        return {
            "success": False,
            "status": "critical_blocked",
            "message": "I can't perform destructive, payment, password, banking, or account automation.",
            "trust_level": "critical",
            "required_action": "blocked",
        }
    return {
        "success": False,
        "status": "unsupported",
        "message": "I can't perform that action yet.",
        "error": "Unsupported action type.",
    }


def execute_action_plan(
    plan: ActionPlan,
    *,
    session_id: str | None = None,
    username: str | None = None,
    automation_confirmed: bool = False,
) -> Dict[str, Any]:
    feedback: List[str] = []
    completed = 0
    failed_step: Optional[Dict[str, Any]] = None
    plan.status = "running"
    has_control_steps = any(step.action_type in CONTROL_ACTION_TYPES for step in plan.steps)
    if automation_confirmed:
        reset_stop_flag()

    for step in plan.steps:
        running_message = _running_message(step)
        step.status = "running"
        step.message = running_message
        feedback.append(running_message)

        result = _execute_step_with_retry_and_recovery(step, automation_confirmed=automation_confirmed)
        step.result = dict(result)
        if _is_verified_success(step, result):
            step.status = "success"
            step.message = str(result.get("message") or running_message).strip()
            completed += 1
            recovery_message = str(result.get("recovery_message") or "").strip()
            if recovery_message:
                feedback.append(recovery_message)
            if has_control_steps and step is not plan.steps[-1]:
                time.sleep(ACTION_STEP_COOLDOWN_SECONDS)
            continue

        failure_message = str(result.get("message") or "That step failed.").strip()
        step.status = "pending" if str(result.get("status") or "") == "needs_confirmation" else "failed"
        step.message = failure_message
        if failure_message and failure_message != running_message:
            feedback.append(failure_message)
        failed_step = step.to_dict()
        break

    if failed_step:
        for step in plan.steps[completed + 1 :]:
            step.status = "skipped"
            step.message = "Skipped because an earlier step failed."
        failed_status = str((failed_step.get("result") or {}).get("status") or "")
        plan.status = "needs_confirmation" if failed_status == "needs_confirmation" else "failed"
    else:
        plan.status = "completed"

    plan_dict = plan.to_dict()
    memory_summary = record_action_plan(plan_dict, session_id=session_id, username=username)
    suggestions = get_action_suggestions(plan_dict, limit=3)

    return {
        "success": failed_step is None,
        "status": plan.status,
        "completed_steps": completed,
        "total_steps": len(plan.steps),
        "failed_step": failed_step,
        "feedback": feedback,
        "plan": plan_dict,
        "action_memory": memory_summary,
        "suggestions": suggestions,
        "automation_confirmation_required": plan.status == "needs_confirmation",
        "automation_control": any(step.get("action_type") in CONTROL_ACTION_TYPES for step in plan_dict.get("steps", [])),
    }


def _is_verified_success(step: ActionStep, result: Dict[str, Any]) -> bool:
    if not result.get("success"):
        return False
    if step.action_type.startswith("automation_"):
        return True
    if step.action_type == "browser_new_tab":
        return bool(result.get("verified"))
    if step.action_type.startswith("browser_"):
        return bool(result.get("verified")) and str(result.get("url") or "").startswith(("http://", "https://"))
    return True


def _execute_step_with_retry(step: ActionStep, *, automation_confirmed: bool = False) -> Dict[str, Any]:
    first = _execute_step(step, automation_confirmed=automation_confirmed)
    if _is_verified_success(step, first):
        first["attempts"] = 1
        if step.action_type.startswith("automation_"):
            first["single_execution"] = True
        return first

    if step.action_type.startswith("automation_"):
        first["attempts"] = 1
        first["single_execution"] = True
        return first

    second = _execute_step(step, automation_confirmed=automation_confirmed)
    if not second.get("success") and not second.get("message"):
        second["message"] = first.get("message") or "That step failed."
    second["attempts"] = 2
    second["first_attempt"] = {
        "status": first.get("status"),
        "message": first.get("message"),
        "verified": first.get("verified"),
    }
    return second


def _execute_step_with_retry_and_recovery(step: ActionStep, *, automation_confirmed: bool = False) -> Dict[str, Any]:
    result = _execute_step_with_retry(step, automation_confirmed=automation_confirmed)
    if _is_verified_success(step, result):
        return result

    recovery = _recover_failed_step(step, result)
    if recovery and _is_verified_success(step, recovery):
        recovery["recovered"] = True
        recovery["recovered_from"] = {
            "status": result.get("status"),
            "message": result.get("message"),
        }
        recovery["recovery_message"] = str(
            recovery.get("recovery_message")
            or recovery.get("message")
            or "I used a safe fallback for that step."
        )
        return recovery
    return result


def _recover_failed_step(step: ActionStep, result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if step.action_type != "browser_open_result" or not step.target:
        return None
    if result.get("status") == "unavailable":
        return None
    fallback = search_query(step.target)
    if fallback.get("success"):
        fallback["status"] = "recovered_search"
        fallback["recovery_message"] = (
            f"I couldn't open that specific result, so I opened the safe Google search page for {step.target} instead."
        )
        fallback["message"] = fallback["recovery_message"]
    return fallback
