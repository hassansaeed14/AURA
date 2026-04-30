from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from brain.command_splitter import split_commands
from tools.desktop_controller import (
    get_application_label,
    normalize_application_name,
    open_application,
    open_chrome_search,
)


OPEN_ACTION_RE = re.compile(
    r"^(?:please\s+)?(?:open|launch|start)\s+(?:the\s+)?(?P<target>[a-z0-9 .-]+?)(?:\s+(?:app|application|browser))?[.!?]*$",
    flags=re.IGNORECASE,
)
SEARCH_ACTION_RE = re.compile(
    r"^(?:please\s+)?(?:(?:search|google|look\s+up|find)\s+(?:for\s+)?|search\s+the\s+web\s+for\s+)(?P<query>.+?)\s*[.!?]*$",
    flags=re.IGNORECASE,
)
SAFE_ACTION_TYPES = {"desktop_open", "browser_search"}


@dataclass
class ActionStep:
    step_id: str
    action_type: str
    target: str
    label: str
    source_text: str
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


def parse_action_step(fragment: str, index: int) -> Optional[ActionStep]:
    return _parse_open_step(fragment, index) or _parse_search_step(fragment, index)


def build_action_plan(command: str) -> Optional[ActionPlan]:
    fragments = split_commands(command)
    if len(fragments) < 2:
        return None

    steps: List[ActionStep] = []
    for index, fragment in enumerate(fragments, start=1):
        step = parse_action_step(fragment, index)
        if step is None or step.action_type not in SAFE_ACTION_TYPES:
            return None
        steps.append(step)

    if len(steps) < 2:
        return None
    return ActionPlan(plan_id=_plan_id(command), original_command=str(command or "").strip(), steps=steps)


def _running_message(step: ActionStep) -> str:
    if step.action_type == "desktop_open":
        return f"Opening {step.label.replace('Open ', '')}..."
    if step.action_type == "browser_search":
        return f"Searching for {step.target}..."
    return f"Running {step.label}..."


def _execute_step(step: ActionStep) -> Dict[str, Any]:
    if step.action_type == "desktop_open":
        return open_application(step.target)
    if step.action_type == "browser_search":
        return open_chrome_search(step.target)
    return {
        "success": False,
        "status": "unsupported",
        "message": "I can't perform that action yet.",
        "error": "Unsupported action type.",
    }


def execute_action_plan(plan: ActionPlan) -> Dict[str, Any]:
    feedback: List[str] = []
    completed = 0
    failed_step: Optional[Dict[str, Any]] = None
    plan.status = "running"

    for step in plan.steps:
        running_message = _running_message(step)
        step.status = "running"
        step.message = running_message
        feedback.append(running_message)

        result = _execute_step(step)
        step.result = dict(result)
        if result.get("success"):
            step.status = "completed"
            completed += 1
            continue

        step.status = "failed"
        failure_message = str(result.get("message") or "That step failed.").strip()
        step.message = failure_message
        if failure_message and failure_message != running_message:
            feedback.append(failure_message)
        failed_step = step.to_dict()
        break

    if failed_step:
        for step in plan.steps[completed + 1 :]:
            step.status = "skipped"
            step.message = "Skipped because an earlier step failed."
        plan.status = "failed"
    else:
        plan.status = "completed"

    return {
        "success": failed_step is None,
        "status": plan.status,
        "completed_steps": completed,
        "total_steps": len(plan.steps),
        "failed_step": failed_step,
        "feedback": feedback,
        "plan": plan.to_dict(),
    }
