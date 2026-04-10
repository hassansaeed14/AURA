from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, List


@dataclass(frozen=True)
class SystemMode:
    key: str
    label: str
    show_intelligence: bool
    show_debug: bool
    show_autonomy: bool
    voice_first: bool
    simplified_ui: bool = False
    restricted_actions: tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


SYSTEM_MODES: Dict[str, SystemMode] = {
    "minimal": SystemMode("minimal", "Minimal Mode", False, False, False, False, simplified_ui=True),
    "smart": SystemMode("smart", "Smart Mode", True, False, True, False),
    "jarvis": SystemMode("jarvis", "Jarvis Mode", True, False, True, True),
    "developer": SystemMode("developer", "Developer Mode", True, True, True, False),
    "autonomous": SystemMode("autonomous", "Autonomous Mode", True, True, True, False),
    "restricted": SystemMode(
        "restricted",
        "Restricted Mode",
        True,
        True,
        False,
        False,
        restricted_actions=("purchase", "payment", "file_delete", "system_control", "pc_control"),
    ),
}


def get_system_mode(mode_name: str | None) -> SystemMode:
    normalized = str(mode_name or "smart").strip().lower()
    return SYSTEM_MODES.get(normalized, SYSTEM_MODES["smart"])


def list_system_modes() -> List[Dict[str, object]]:
    return [mode.to_dict() for mode in SYSTEM_MODES.values()]
