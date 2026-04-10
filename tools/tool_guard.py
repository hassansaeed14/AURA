from __future__ import annotations

from typing import Any, Dict

from security.access_control import evaluate_access
from tools.tool_registry import get_tool


def guard_and_execute(
    tool_name: str,
    *,
    username: str | None = None,
    session_id: str = "default",
    confirmed: bool = False,
    pin: str | None = None,
    resource_id: str | None = None,
    **kwargs: Any,
) -> Dict[str, object]:
    record = get_tool(tool_name)
    if record is None:
        return {"success": False, "status": "missing_tool", "reason": f"Unknown tool: {tool_name}"}

    access = evaluate_access(
        record.action_name,
        username=username,
        session_id=session_id,
        confirmed=confirmed,
        pin=pin,
        resource_id=resource_id,
    )
    if not access["success"]:
        return {"success": False, "status": access["status"], "reason": access["reason"], "access": access}

    missing_inputs = [name for name in record.required_inputs if name not in kwargs]
    if missing_inputs:
        return {
            "success": False,
            "status": "missing_inputs",
            "reason": f"Missing required inputs: {', '.join(missing_inputs)}",
            "access": access,
        }

    try:
        result = record.handler(**kwargs)
    except Exception as error:
        return {"success": False, "status": "execution_error", "reason": str(error), "access": access}

    return {"success": True, "status": "executed", "result": result, "access": access}
