from __future__ import annotations

import shlex
import subprocess
from pathlib import Path
from typing import Any, Dict, Iterable, List

from tools.validation_tools import validate_workspace_path


ALLOWED_COMMANDS = {"python", "python.exe", "git", "dir", "tasklist", "where"}


def _normalize_command(command: str | Iterable[str]) -> List[str]:
    if isinstance(command, str):
        return shlex.split(command, posix=False)
    return [str(part) for part in command]


def execute_command(
    command: str | Iterable[str],
    *,
    cwd: str | Path | None = None,
    timeout: int = 15,
) -> Dict[str, Any]:
    args = _normalize_command(command)
    if not args:
        return {"success": False, "status": "missing_command", "message": "Command is required."}

    binary = args[0].lower()
    if binary not in ALLOWED_COMMANDS:
        return {"success": False, "status": "blocked_command", "message": f"{args[0]} is not on the bounded execution allowlist."}

    working_dir = Path(cwd or Path.cwd()).resolve()
    if not validate_workspace_path(working_dir):
        return {"success": False, "status": "invalid_cwd", "message": "Execution cwd is outside the workspace."}

    result = subprocess.run(
        args,
        cwd=str(working_dir),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    return {
        "success": result.returncode == 0,
        "status": "completed" if result.returncode == 0 else "failed",
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
        "command": args,
    }
