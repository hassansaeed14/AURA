from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional

from brain.capability_registry import get_capability
from brain.command_splitter import split_commands
from brain.confidence_engine import evaluate_confidence
from brain.entity_parser import parse_entities
from config.limits_config import MAX_PLAN_STEPS


DEPENDENCY_MARKERS = ("it", "that", "this", "them", "same", "those")


@dataclass(slots=True)
class PlanStep:
    step_id: int
    command: str
    intent: str
    action: str
    agent: str
    depends_on: List[int] = field(default_factory=list)
    ready: bool = True
    reason: str = ""

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass(slots=True)
class ExecutionPlan:
    original_command: str
    steps: List[PlanStep]
    ready: bool
    blocked_reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        payload = asdict(self)
        payload["steps"] = [step.to_dict() for step in self.steps]
        return payload


def _depends_on_previous(command: str) -> bool:
    lowered = command.lower()
    return any(f" {marker}" in f" {lowered}" for marker in DEPENDENCY_MARKERS)


def build_execution_plan(command: str) -> ExecutionPlan:
    sub_commands = split_commands(command) or [str(command or "").strip()]
    steps: List[PlanStep] = []
    blocked_reasons: List[str] = []

    for index, sub_command in enumerate(sub_commands[:MAX_PLAN_STEPS], start=1):
        confidence = evaluate_confidence(sub_command)
        capability = get_capability(confidence.intent) or get_capability("general")
        entities = parse_entities(sub_command)
        required_inputs = list(capability.required_inputs if capability else ())
        missing_inputs = [
            required
            for required in required_inputs
            if not getattr(entities, required, None) and required != "topic"
        ]
        if "topic" in required_inputs and not (entities.primary_topic or entities.topics or entities.files or entities.urls):
            missing_inputs.append("topic")

        ready = capability is not None and capability.capability_mode != "placeholder" and not missing_inputs
        reason = ""
        if capability is None:
            reason = "unknown_capability"
        elif capability.capability_mode == "placeholder":
            reason = "placeholder_capability"
        elif missing_inputs:
            reason = f"missing_inputs:{', '.join(sorted(set(missing_inputs)))}"

        if reason:
            blocked_reasons.append(f"Step {index}: {reason}")

        depends_on = [index - 1] if index > 1 and _depends_on_previous(sub_command) else []
        action = capability.supported_actions[0] if capability and capability.supported_actions else confidence.intent

        steps.append(
            PlanStep(
                step_id=index,
                command=sub_command,
                intent=confidence.intent,
                action=action,
                agent=capability.agent if capability else "general",
                depends_on=depends_on,
                ready=ready,
                reason=reason,
            )
        )

    return ExecutionPlan(
        original_command=str(command or ""),
        steps=steps,
        ready=not blocked_reasons,
        blocked_reasons=blocked_reasons,
    )


def summarize_execution_plan(command: str) -> List[str]:
    plan = build_execution_plan(command)
    summaries = []
    for step in plan.steps:
        dependency_suffix = f" after step {step.depends_on[0]}" if step.depends_on else ""
        readiness = "ready" if step.ready else step.reason
        summaries.append(f"Step {step.step_id}: {step.agent} -> {step.action}{dependency_suffix} [{readiness}]")
    return summaries
