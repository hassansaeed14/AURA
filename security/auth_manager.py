from __future__ import annotations

from typing import Dict

from api.auth import get_user, login_user


def validate_login(username: str, password: str) -> Dict[str, object]:
    success, result = login_user(username, password)
    return {"success": success, "user": result if success else None, "reason": None if success else result}


def get_auth_state(username: str | None) -> Dict[str, object]:
    if not username:
        return {"authenticated": False, "user": None}
    user = get_user(username)
    return {"authenticated": bool(user), "user": user}
