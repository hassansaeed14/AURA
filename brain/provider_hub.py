from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Iterable, List, Optional

import requests

from config.settings import (
    ANTHROPIC_API_KEY,
    DEFAULT_REASONING_PROVIDER,
    GEMINI_API_KEY,
    GROQ_API_KEY,
    OLLAMA_BASE_URL,
    OPENAI_API_KEY,
    PROVIDER_MODEL_MAP,
    PROVIDER_PRIORITY,
)

try:
    from groq import Groq  # type: ignore
except Exception:  # pragma: no cover
    Groq = None

try:
    from openai import OpenAI  # type: ignore
except Exception:  # pragma: no cover
    OpenAI = None


SUPPORTED_PROVIDERS = ("openai", "groq", "claude", "gemini", "ollama")
DEFAULT_TIMEOUT = 30


@dataclass(slots=True)
class ProviderStatus:
    provider: str
    model: str
    mode: str
    configured: bool
    available: bool
    installed: bool
    reason: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ProviderError(Exception):
    pass


def _bool_text(value: bool) -> str:
    return "ready" if value else "unavailable"


def _provider_model(provider: str) -> str:
    return PROVIDER_MODEL_MAP.get(provider, "unknown")


def _provider_installed(provider: str) -> bool:
    if provider == "openai":
        return OpenAI is not None
    if provider == "groq":
        return Groq is not None
    if provider in {"claude", "gemini"}:
        return True
    if provider == "ollama":
        return True
    return False


def _provider_configured(provider: str) -> bool:
    if provider == "openai":
        return bool(OPENAI_API_KEY)
    if provider == "groq":
        return bool(GROQ_API_KEY)
    if provider == "claude":
        return bool(ANTHROPIC_API_KEY)
    if provider == "gemini":
        return bool(GEMINI_API_KEY)
    if provider == "ollama":
        return bool(OLLAMA_BASE_URL)
    return False


def get_provider_status(provider: str) -> ProviderStatus:
    normalized = str(provider or "").strip().lower()
    installed = _provider_installed(normalized)
    configured = _provider_configured(normalized)
    available = installed and configured
    if normalized == "ollama":
        available = configured

    if available:
        reason = f"{normalized} provider is {_bool_text(True)}."
    elif not installed:
        reason = f"{normalized} SDK is not installed."
    elif not configured:
        if normalized == "ollama":
            reason = "Ollama base URL is missing."
        else:
            reason = f"{normalized} API key is missing."
    else:
        reason = f"{normalized} provider is unavailable."

    return ProviderStatus(
        provider=normalized,
        model=_provider_model(normalized),
        mode="real" if normalized == "ollama" and available else "hybrid",
        configured=configured,
        available=available,
        installed=installed,
        reason=reason,
    )


def list_provider_statuses() -> List[Dict[str, Any]]:
    return [get_provider_status(provider).to_dict() for provider in SUPPORTED_PROVIDERS]


def summarize_provider_statuses() -> Dict[str, Any]:
    statuses = list_provider_statuses()
    available = [item["provider"] for item in statuses if item["available"]]
    configured = [item["provider"] for item in statuses if item["configured"]]
    return {
        "default_provider": DEFAULT_REASONING_PROVIDER,
        "priority": list(PROVIDER_PRIORITY),
        "available": available,
        "configured": configured,
        "items": statuses,
    }


def _preferred_provider_order(preferred: Optional[str] = None) -> List[str]:
    desired = str(preferred or DEFAULT_REASONING_PROVIDER or "router").strip().lower()
    if desired and desired not in {"router", "auto"} and desired in SUPPORTED_PROVIDERS:
        ordered = [desired]
    else:
        ordered = []
    for provider in PROVIDER_PRIORITY:
        if provider in SUPPORTED_PROVIDERS and provider not in ordered:
            ordered.append(provider)
    for provider in SUPPORTED_PROVIDERS:
        if provider not in ordered:
            ordered.append(provider)
    return ordered


def pick_provider(preferred: Optional[str] = None) -> Optional[str]:
    for provider in _preferred_provider_order(preferred):
        if get_provider_status(provider).available:
            return provider
    return None


def _message_text(messages: Iterable[Dict[str, str]], role: str) -> str:
    return "\n".join(
        str(item.get("content", "")).strip()
        for item in messages
        if str(item.get("role", "")).strip() == role and str(item.get("content", "")).strip()
    ).strip()


def _messages_to_prompt(messages: List[Dict[str, str]]) -> str:
    parts = []
    for item in messages:
        role = str(item.get("role", "user")).strip().title()
        content = str(item.get("content", "")).strip()
        if content:
            parts.append(f"{role}: {content}")
    return "\n\n".join(parts).strip()


def _call_openai(messages: List[Dict[str, str]], *, max_tokens: int, temperature: float) -> Dict[str, Any]:
    if OpenAI is None or not OPENAI_API_KEY:
        raise ProviderError("OpenAI provider is not configured.")
    client = OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
        model=_provider_model("openai"),
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    text = response.choices[0].message.content or ""
    return {"success": True, "provider": "openai", "model": _provider_model("openai"), "text": str(text).strip()}


def _call_groq(messages: List[Dict[str, str]], *, max_tokens: int, temperature: float) -> Dict[str, Any]:
    if Groq is None or not GROQ_API_KEY:
        raise ProviderError("Groq provider is not configured.")
    client = Groq(api_key=GROQ_API_KEY)
    response = client.chat.completions.create(
        model=_provider_model("groq"),
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    text = response.choices[0].message.content or ""
    return {"success": True, "provider": "groq", "model": _provider_model("groq"), "text": str(text).strip()}


def _call_claude(messages: List[Dict[str, str]], *, max_tokens: int, temperature: float) -> Dict[str, Any]:
    if not ANTHROPIC_API_KEY:
        raise ProviderError("Claude provider is not configured.")
    system_prompt = _message_text(messages, "system")
    non_system = [item for item in messages if item.get("role") != "system"]
    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        timeout=DEFAULT_TIMEOUT,
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": _provider_model("claude"),
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": system_prompt,
            "messages": non_system,
        },
    )
    response.raise_for_status()
    payload = response.json()
    text_parts = []
    for item in payload.get("content", []):
        if item.get("type") == "text":
            text_parts.append(str(item.get("text", "")).strip())
    return {
        "success": True,
        "provider": "claude",
        "model": _provider_model("claude"),
        "text": "\n".join(part for part in text_parts if part).strip(),
    }


def _call_gemini(messages: List[Dict[str, str]], *, max_tokens: int, temperature: float) -> Dict[str, Any]:
    if not GEMINI_API_KEY:
        raise ProviderError("Gemini provider is not configured.")
    system_prompt = _message_text(messages, "system")
    user_prompt = _messages_to_prompt([item for item in messages if item.get("role") != "system"])
    response = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{_provider_model('gemini')}:generateContent",
        timeout=DEFAULT_TIMEOUT,
        params={"key": GEMINI_API_KEY},
        headers={"content-type": "application/json"},
        json={
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        },
    )
    response.raise_for_status()
    payload = response.json()
    candidates = payload.get("candidates") or []
    first = candidates[0] if candidates else {}
    parts = (((first.get("content") or {}).get("parts")) or [])
    text = "\n".join(str(part.get("text", "")).strip() for part in parts if part.get("text"))
    return {
        "success": True,
        "provider": "gemini",
        "model": _provider_model("gemini"),
        "text": text.strip(),
    }


def _call_ollama(messages: List[Dict[str, str]], *, max_tokens: int, temperature: float) -> Dict[str, Any]:
    if not OLLAMA_BASE_URL:
        raise ProviderError("Ollama base URL is not configured.")
    system_prompt = _message_text(messages, "system")
    prompt = _messages_to_prompt([item for item in messages if item.get("role") != "system"])
    response = requests.post(
        f"{OLLAMA_BASE_URL.rstrip('/')}/api/generate",
        timeout=DEFAULT_TIMEOUT,
        headers={"content-type": "application/json"},
        json={
            "model": _provider_model("ollama"),
            "system": system_prompt,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        },
    )
    response.raise_for_status()
    payload = response.json()
    text = payload.get("response", "")
    return {
        "success": True,
        "provider": "ollama",
        "model": _provider_model("ollama"),
        "text": str(text).strip(),
    }


def generate_with_provider(
    provider: str,
    messages: List[Dict[str, str]],
    *,
    max_tokens: int,
    temperature: float,
) -> Dict[str, Any]:
    normalized = str(provider or "").strip().lower()
    if normalized == "openai":
        return _call_openai(messages, max_tokens=max_tokens, temperature=temperature)
    if normalized == "groq":
        return _call_groq(messages, max_tokens=max_tokens, temperature=temperature)
    if normalized == "claude":
        return _call_claude(messages, max_tokens=max_tokens, temperature=temperature)
    if normalized == "gemini":
        return _call_gemini(messages, max_tokens=max_tokens, temperature=temperature)
    if normalized == "ollama":
        return _call_ollama(messages, max_tokens=max_tokens, temperature=temperature)
    raise ProviderError(f"Unknown provider: {provider}")


def generate_with_best_provider(
    messages: List[Dict[str, str]],
    *,
    preferred: Optional[str] = None,
    max_tokens: int,
    temperature: float,
) -> Dict[str, Any]:
    attempts: List[Dict[str, str]] = []
    for provider in _preferred_provider_order(preferred):
        status = get_provider_status(provider)
        if not status.available:
            attempts.append({"provider": provider, "status": "skipped", "reason": status.reason})
            continue
        try:
            result = generate_with_provider(provider, messages, max_tokens=max_tokens, temperature=temperature)
            result["attempts"] = attempts + [{"provider": provider, "status": "used", "reason": "success"}]
            return result
        except Exception as error:
            attempts.append({"provider": provider, "status": "failed", "reason": str(error)})

    return {
        "success": False,
        "provider": None,
        "model": None,
        "text": "",
        "attempts": attempts,
        "reason": "No configured provider produced a response.",
    }
