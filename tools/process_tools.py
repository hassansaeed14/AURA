from __future__ import annotations

import csv
import io
import subprocess
from pathlib import Path
from typing import Any, Dict, List


ALLOWLISTED_APPS = {
    "notepad": ["notepad.exe"],
    "calculator": ["calc.exe"],
    "paint": ["mspaint.exe"],
    "explorer": ["explorer.exe"],
    "chrome": ["chrome.exe"],
    "edge": ["msedge.exe"],
}


def _run_tasklist() -> str:
    result = subprocess.run(
        ["tasklist", "/fo", "csv", "/nh"],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    return result.stdout or ""


def list_processes(*, limit: int = 50, name_filter: str | None = None) -> List[Dict[str, Any]]:
    rows = csv.reader(io.StringIO(_run_tasklist()))
    matches: List[Dict[str, Any]] = []
    filter_value = str(name_filter or "").strip().lower()

    for row in rows:
        if len(row) < 5:
            continue
        image_name, pid, session_name, session_num, mem_usage = row[:5]
        if filter_value and filter_value not in image_name.lower():
            continue
        matches.append(
            {
                "image_name": image_name,
                "pid": int(pid) if str(pid).isdigit() else pid,
                "session_name": session_name,
                "session_number": session_num,
                "memory_usage": mem_usage,
            }
        )
        if len(matches) >= limit:
            break
    return matches


def is_process_running(name: str) -> bool:
    target = str(name or "").strip().lower()
    if not target:
        return False
    return any(target in str(item["image_name"]).lower() for item in list_processes(limit=500))


def open_application(app_name: str, *, launch: bool = False, args: list[str] | None = None) -> Dict[str, Any]:
    normalized = str(app_name or "").strip().lower().replace(".exe", "")
    command = ALLOWLISTED_APPS.get(normalized)
    if command is None:
        return {"success": False, "status": "not_allowlisted", "message": f"{app_name} is not on the bounded allowlist."}

    final_command = command + list(args or [])
    if not launch:
        return {
            "success": True,
            "status": "preview",
            "command": final_command,
            "message": "App launch preview prepared. Launch is disabled until explicitly requested.",
        }

    subprocess.Popen(final_command, cwd=str(Path.cwd()))
    return {"success": True, "status": "launched", "command": final_command, "message": f"Launched {app_name}."}


def close_application(name: str, *, force: bool = False) -> Dict[str, Any]:
    normalized = str(name or "").strip()
    if not normalized:
        return {"success": False, "status": "missing_name", "message": "App name is required."}

    command = ["taskkill", "/im", normalized]
    if force:
        command.append("/f")
    result = subprocess.run(command, capture_output=True, text=True, timeout=10, check=False)
    return {
        "success": result.returncode == 0,
        "status": "closed" if result.returncode == 0 else "failed",
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }
