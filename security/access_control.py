from __future__ import annotations

from typing import Dict, Optional

from security.audit_logger import record_audit_event
from security.auth_manager import get_auth_state
from security.lock_manager import is_locked
from security.pin_manager import verify_pin
from security.session_manager import is_action_approved
from security.trust_engine import ApprovalType, evaluate_action


def evaluate_access(
    action_name: str,
    *,
    username: str | None = None,
    session_id: str = "default",
    confirmed: bool = False,
    pin: str | None = None,
    resource_id: str | None = None,
) -> Dict[str, object]:
    auth_state = get_auth_state(username)
    if resource_id and is_locked(resource_id):
        event = record_audit_event(
            action_name=action_name,
            allowed=False,
            trust_level="critical",
            reason="resource_locked",
            username=username,
            session_id=session_id,
        )
        return {"success": False, "status": "locked", "reason": "Resource is locked.", "audit": event}

    pin_result = verify_pin(pin) if pin else {"success": False}
    decision = evaluate_action(
        action_name,
        confirmed=confirmed,
        session_approved=is_action_approved(session_id, action_name),
        pin_verified=bool(pin_result.get("success")),
    )

    if decision.approval_type != ApprovalType.NONE and username and not auth_state["authenticated"]:
        event = record_audit_event(
            action_name=action_name,
            allowed=False,
            trust_level=decision.trust_level.value,
            reason="authentication_required",
            username=username,
            session_id=session_id,
        )
        return {"success": False, "status": "auth_required", "reason": "Authentication required for this action.", "decision": decision.to_dict(), "audit": event}

    event = record_audit_event(
        action_name=action_name,
        allowed=decision.allowed,
        trust_level=decision.trust_level.value,
        reason=decision.reason_code,
        username=username,
        session_id=session_id,
    )
    return {
        "success": decision.allowed,
        "status": "approved" if decision.allowed else decision.approval_type.value,
        "reason": decision.reason,
        "decision": decision.to_dict(),
        "audit": event,
    }
