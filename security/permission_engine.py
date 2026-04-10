import json
import os
from datetime import datetime, timedelta

PERMISSIONS_FILE = "memory/permissions.json"


def default_permissions():
    return {
        "policy_mode": "balanced",
        "action_rules": {
            "safe": "allow",
            "private": "ask",
            "sensitive": "session",
            "critical": "pin"
        },
        "trusted_sessions": {},
        "custom_rules": {}
    }


def load_permissions():
    if not os.path.exists(PERMISSIONS_FILE):
        return default_permissions()

    try:
        with open(PERMISSIONS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return default_permissions()

    default = default_permissions()
    for key, value in default.items():
        if key not in data:
            data[key] = value

    return data


def save_permissions(data):
    os.makedirs(os.path.dirname(PERMISSIONS_FILE), exist_ok=True)
    with open(PERMISSIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def get_policy_mode():
    data = load_permissions()
    return data.get("policy_mode", "balanced")


def set_policy_mode(mode):
    mode = str(mode).strip().lower()
    if mode not in ["relaxed", "balanced", "strict", "custom"]:
        return False

    data = load_permissions()
    data["policy_mode"] = mode

    if mode == "relaxed":
        data["action_rules"] = {
            "safe": "allow",
            "private": "allow",
            "sensitive": "ask",
            "critical": "pin"
        }
    elif mode == "balanced":
        data["action_rules"] = {
            "safe": "allow",
            "private": "ask",
            "sensitive": "session",
            "critical": "pin"
        }
    elif mode == "strict":
        data["action_rules"] = {
            "safe": "ask",
            "private": "ask",
            "sensitive": "pin",
            "critical": "pin"
        }

    save_permissions(data)
    return True


def classify_action(command: str):
    text = str(command).lower()

    critical_keywords = [
        "buy", "purchase", "pay", "payment", "send money",
        "use card", "credit card", "debit card",
        "unlock locked chat", "show locked chats",
        "delete all files", "wipe", "factory reset"
    ]

    sensitive_keywords = [
        "login", "log in", "sign in", "open private chat",
        "send message to all", "mass message", "post this",
        "access account", "read private messages",
        "open email", "read email", "send email"
    ]

    private_keywords = [
        "open whatsapp", "open snapchat", "open facebook",
        "open instagram", "open gallery", "open photos",
        "open files", "show my history", "show my chats"
    ]

    safe_keywords = [
        "open", "play", "pause", "resume", "skip",
        "next song", "weather", "news", "joke", "quote",
        "translate", "summarize", "define", "search"
    ]

    if any(k in text for k in critical_keywords):
        return "critical"

    if any(k in text for k in sensitive_keywords):
        return "sensitive"

    if any(k in text for k in private_keywords):
        return "private"

    if any(k in text for k in safe_keywords):
        return "safe"

    return "private"


def get_action_rule(action_level: str, command: str = None):
    data = load_permissions()

    if command:
        cmd_key = str(command).strip().lower()
        if cmd_key in data.get("custom_rules", {}):
            return data["custom_rules"][cmd_key]

    return data.get("action_rules", {}).get(action_level, "ask")


def allow_for_session(command: str, minutes=30):
    data = load_permissions()
    expires = datetime.now() + timedelta(minutes=minutes)

    data["trusted_sessions"][command.strip().lower()] = {
        "expires_at": expires.strftime("%Y-%m-%d %H:%M:%S")
    }

    save_permissions(data)


def is_session_allowed(command: str):
    data = load_permissions()
    trusted = data.get("trusted_sessions", {})
    key = command.strip().lower()

    if key not in trusted:
        return False

    try:
        expires = datetime.strptime(trusted[key]["expires_at"], "%Y-%m-%d %H:%M:%S")
        if datetime.now() <= expires:
            return True
    except Exception:
        pass

    trusted.pop(key, None)
    data["trusted_sessions"] = trusted
    save_permissions(data)
    return False


def set_custom_rule(command: str, rule: str):
    rule = str(rule).strip().lower()
    if rule not in ["allow", "ask", "session", "pin", "deny"]:
        return False

    data = load_permissions()
    data["custom_rules"][command.strip().lower()] = rule
    data["policy_mode"] = "custom"
    save_permissions(data)
    return True


def evaluate_permission(command: str):
    action_level = classify_action(command)

    if is_session_allowed(command):
        return {
            "allowed": True,
            "action_level": action_level,
            "rule": "session",
            "reason": "Previously approved for this session."
        }

    rule = get_action_rule(action_level, command)

    if rule == "allow":
        return {
            "allowed": True,
            "action_level": action_level,
            "rule": rule,
            "reason": "This action is allowed by current policy."
        }

    if rule == "ask":
        return {
            "allowed": False,
            "action_level": action_level,
            "rule": rule,
            "reason": "This action needs user confirmation."
        }

    if rule == "session":
        return {
            "allowed": False,
            "action_level": action_level,
            "rule": rule,
            "reason": "This action needs session approval."
        }

    if rule == "pin":
        return {
            "allowed": False,
            "action_level": action_level,
            "rule": rule,
            "reason": "This action requires PIN or password confirmation."
        }

    return {
        "allowed": False,
        "action_level": action_level,
        "rule": "deny",
        "reason": "This action is blocked by policy."
    }