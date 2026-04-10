from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple


TRUST_LEVELS: Tuple[str, ...] = ("safe", "private", "sensitive", "critical")
VALID_PERMISSION_RULES: Tuple[str, ...] = ("allow", "ask", "session", "pin", "deny")

DEFAULT_PERMISSION_RULES: Dict[str, str] = {
    "safe": "allow",
    "private": "ask",
    "sensitive": "session",
    "critical": "pin",
}

ACTION_GROUPS: Dict[str, Tuple[str, ...]] = {
    "safe": (
        "general",
        "greeting",
        "identity",
        "time",
        "date",
        "weather",
        "news",
        "math",
        "translation",
        "research",
        "study",
        "code",
        "summarize",
        "task_read",
        "task_add",
        "task_complete",
        "reminder_read",
        "reminder_add",
        "reminder_complete",
        "password",
    ),
    "private": (
        "memory_read",
        "history",
        "file_read",
        "file_list",
        "profile_read",
    ),
    "sensitive": (
        "auth_login",
        "auth_register",
        "memory_write",
        "settings_update",
        "screenshot",
        "file_write",
        "executor",
    ),
    "critical": (
        "payment",
        "purchase",
        "system_control",
        "pc_control",
        "file_delete",
        "account_delete",
        "locked_chat_unlock",
    ),
}

ACTION_TRUST_MAP: Dict[str, str] = {
    action_name: trust_level
    for trust_level, actions in ACTION_GROUPS.items()
    for action_name in actions
}


@dataclass(frozen=True)
class PermissionProfile:
    trust_level: str
    rule: str

    def to_dict(self) -> Dict[str, str]:
        return {"trust_level": self.trust_level, "rule": self.rule}


def normalize_trust_level(value: str | None) -> str:
    normalized = str(value or "sensitive").strip().lower()
    return normalized if normalized in TRUST_LEVELS else "sensitive"


def normalize_rule(value: str | None) -> str:
    normalized = str(value or "ask").strip().lower()
    return normalized if normalized in VALID_PERMISSION_RULES else "ask"


def get_default_permission_rules() -> Dict[str, str]:
    return dict(DEFAULT_PERMISSION_RULES)


def get_action_trust_level(action_name: str | None) -> str:
    normalized = str(action_name or "general").strip().lower().replace(" ", "_")
    return ACTION_TRUST_MAP.get(normalized, "sensitive")


def get_rule_for_trust_level(trust_level: str | None, overrides: Dict[str, str] | None = None) -> str:
    normalized = normalize_trust_level(trust_level)
    rules = get_default_permission_rules()
    if overrides:
        for key, value in overrides.items():
            rules[normalize_trust_level(key)] = normalize_rule(value)
    return rules.get(normalized, "ask")


def get_permission_profile(action_name: str | None, overrides: Dict[str, str] | None = None) -> PermissionProfile:
    trust_level = get_action_trust_level(action_name)
    return PermissionProfile(
        trust_level=trust_level,
        rule=get_rule_for_trust_level(trust_level, overrides=overrides),
    )
