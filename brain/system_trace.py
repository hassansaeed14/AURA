from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import uuid4


def new_request_id(prefix: str = "aura") -> str:
    """Create a short request id for correlating one user request across layers."""

    normalized = "".join(ch for ch in str(prefix or "aura").lower() if ch.isalnum() or ch == "-").strip("-")
    return f"{normalized or 'aura'}-{uuid4().hex[:12]}"


def _string(value: Any, default: str = "") -> str:
    text = str(value if value is not None else "").strip()
    return text or default


def _permission_state(permission: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not permission:
        return {
            "allowed": None,
            "status": "not_checked",
            "action_name": "unknown",
            "trust_level": "safe",
            "approval_type": "none",
            "required_action": "allow",
        }
    permission = dict(permission or {})
    detail = dict(permission.get("permission") or {})
    return {
        "allowed": bool(permission.get("success", False)),
        "status": _string(permission.get("status"), "unknown"),
        "action_name": _string(detail.get("action_name"), "unknown"),
        "trust_level": _string(detail.get("trust_level"), "safe"),
        "approval_type": _string(detail.get("approval_type"), "none"),
        "required_action": _string(detail.get("required_action"), "allow"),
    }


def _summarize_action_plan(action_plan: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(action_plan, dict):
        return None
    steps = action_plan.get("steps") if isinstance(action_plan.get("steps"), list) else []
    return {
        "present": True,
        "plan_id": _string(action_plan.get("plan_id")),
        "status": _string(action_plan.get("status"), "unknown"),
        "step_count": len(steps),
        "steps": [
            {
                "id": _string(step.get("step_id") or step.get("id"), f"step-{index}"),
                "action_type": _string(step.get("action_type"), "action"),
                "label": _string(step.get("label"), f"Step {index}"),
                "status": _string(step.get("status"), "pending"),
            }
            for index, step in enumerate(steps, start=1)
            if isinstance(step, dict)
        ],
    }


def _infer_automation_state(
    *,
    action_plan: Any,
    automation_state: Optional[Dict[str, Any]],
    permission_state: Dict[str, Any],
    source: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    if automation_state:
        return dict(automation_state)

    source = dict(source or {})
    plan_summary = _summarize_action_plan(action_plan)
    steps = plan_summary.get("steps", []) if plan_summary else []
    action_types = {str(step.get("action_type") or "") for step in steps}
    step_statuses = {str(step.get("status") or "") for step in steps}
    has_control = bool(source.get("automation_control")) or any(item.startswith("automation_") for item in action_types)
    confirmation_required = bool(source.get("automation_confirmation_required")) or any(
        status in {"needs_confirmation", "pending"} and action_type == "automation_confirm"
        for status in step_statuses
        for action_type in action_types
    )
    blocked = (
        permission_state.get("allowed") is False
        or any("blocked" in status for status in step_statuses)
        or any(item == "automation_critical_blocked" for item in action_types)
    )
    return {
        "active": has_control,
        "confirmation_required": confirmation_required,
        "status": _string(source.get("action_status") or (plan_summary or {}).get("status"), "idle"),
        "blocked": bool(blocked),
    }


def infer_response_mode(
    *,
    execution_mode: Optional[str] = None,
    kind: Optional[str] = None,
    action_plan: Any = None,
    document_delivery: Any = None,
    permission_state: Optional[Dict[str, Any]] = None,
    automation_state: Optional[Dict[str, Any]] = None,
    degraded: bool = False,
    error: Optional[str] = None,
) -> str:
    execution = _string(execution_mode).lower()
    if error and execution in {"server_error", "validation_error"}:
        return "error"
    if permission_state and permission_state.get("allowed") is False:
        return "blocked"
    if automation_state and automation_state.get("blocked"):
        return "blocked"
    if document_delivery or kind == "document_delivery" or execution.startswith("document"):
        return "document"
    if automation_state and automation_state.get("confirmation_required"):
        return "control_pending"
    if action_plan:
        return "control" if automation_state and automation_state.get("active") else "action"
    if degraded or execution == "degraded_assistant":
        return "limited_response"
    if execution in {"greeting", "casual_local"}:
        return "conversation"
    return "assistant"


def infer_final_status(
    *,
    success: Optional[bool] = None,
    status: Optional[str] = None,
    permission_state: Optional[Dict[str, Any]] = None,
    automation_state: Optional[Dict[str, Any]] = None,
    degraded: bool = False,
    error: Optional[str] = None,
) -> str:
    normalized_status = _string(status).lower()
    if permission_state and permission_state.get("allowed") is False:
        return "blocked"
    if automation_state and automation_state.get("blocked"):
        return "blocked"
    if automation_state and automation_state.get("confirmation_required"):
        return "pending_approval"
    if degraded:
        return "degraded"
    if error and success is False:
        return "error"
    if normalized_status in {"blocked", "critical_blocked", "permission_blocked"}:
        return "blocked"
    if normalized_status in {"needs_confirmation", "pending_approval"}:
        return "pending_approval"
    if success is False:
        return "error" if error else "failed"
    return "ok"


def build_action_trace(
    *,
    request_id: Optional[str],
    raw_input: str,
    intent: Optional[str],
    provider: Optional[str],
    permission: Optional[Dict[str, Any]] = None,
    action_plan: Any = None,
    response_mode: Optional[str] = None,
    automation_state: Optional[Dict[str, Any]] = None,
    final_status: Optional[str] = None,
    execution_mode: Optional[str] = None,
    used_agents: Optional[list[Any]] = None,
    document_delivery: Any = None,
    kind: Optional[str] = None,
    degraded: bool = False,
    success: Optional[bool] = None,
    status: Optional[str] = None,
    error: Optional[str] = None,
    source: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    permission_snapshot = _permission_state(permission)
    automation_snapshot = _infer_automation_state(
        action_plan=action_plan,
        automation_state=automation_state,
        permission_state=permission_snapshot,
        source=source,
    )
    mode = response_mode or infer_response_mode(
        execution_mode=execution_mode,
        kind=kind,
        action_plan=action_plan,
        document_delivery=document_delivery,
        permission_state=permission_snapshot,
        automation_state=automation_snapshot,
        degraded=degraded,
        error=error,
    )
    status_value = final_status or infer_final_status(
        success=success,
        status=status,
        permission_state=permission_snapshot,
        automation_state=automation_snapshot,
        degraded=degraded,
        error=error,
    )
    if response_mode is None and status_value in {"blocked", "error", "degraded"}:
        mode = "limited_response" if status_value == "degraded" else status_value
    return {
        "request_id": request_id or new_request_id(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "input": _string(raw_input),
        "intent": _string(intent, "general"),
        "provider": _string(provider, "none"),
        "execution_mode": _string(execution_mode, "unknown"),
        "response_mode": mode,
        "permission_state": permission_snapshot,
        "action_plan": _summarize_action_plan(action_plan),
        "automation_state": automation_snapshot,
        "document_state": {
            "present": bool(document_delivery),
            "kind": _string(kind),
        },
        "agents": [str(agent) for agent in (used_agents or []) if str(agent).strip()],
        "degraded": bool(degraded),
        "final_status": status_value,
        "error": _string(error) or None,
    }
