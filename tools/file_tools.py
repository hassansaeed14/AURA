from __future__ import annotations

import shutil
from pathlib import Path
from typing import Dict, List

from tools.validation_tools import validate_workspace_path


def _resolve_path(path_value: str | Path) -> Path:
    candidate = Path(path_value).expanduser().resolve()
    if not validate_workspace_path(candidate):
        raise ValueError("Path is outside the allowed workspace.")
    return candidate


def read_file(path_value: str | Path) -> Dict[str, object]:
    path = _resolve_path(path_value)
    return {
        "path": str(path),
        "content": path.read_text(encoding="utf-8"),
        "size": path.stat().st_size,
    }


def list_directory(path_value: str | Path = ".") -> List[Dict[str, object]]:
    path = _resolve_path(path_value)
    return [
        {
            "name": item.name,
            "path": str(item),
            "is_dir": item.is_dir(),
        }
        for item in sorted(path.iterdir(), key=lambda entry: (not entry.is_dir(), entry.name.lower()))
    ]


def write_file(path_value: str | Path, content: str) -> Dict[str, object]:
    path = _resolve_path(path_value)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(content), encoding="utf-8")
    return {"path": str(path), "written": True}


def delete_file(path_value: str | Path) -> Dict[str, object]:
    path = _resolve_path(path_value)
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()
    return {"path": str(path), "deleted": True}
