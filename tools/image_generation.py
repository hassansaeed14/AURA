from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any, Optional


SUPPORTED_IMAGE_PROVIDERS = ("openai", "stable_diffusion_local")
DEFAULT_IMAGE_SIZE = "1024x1024"
MAX_PROMPT_CHARS = 1200

IMAGE_REQUEST_RE = re.compile(
    r"\b(?:generate|create|make|draw|produce)\b.{0,90}\b(?:image|picture|illustration|artwork|logo|poster|visual)\b"
    r"|\b(?:image|picture|illustration|artwork|logo|poster|visual)\s+of\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ImageProviderStatus:
    provider: str
    configured: bool
    available: bool
    status: str
    reason: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "configured": self.configured,
            "available": self.available,
            "status": self.status,
            "reason": self.reason,
        }


def detect_image_generation_request(text: str) -> bool:
    return bool(IMAGE_REQUEST_RE.search(str(text or "").strip()))


def _configured_provider() -> str:
    provider = os.getenv("AURA_IMAGE_PROVIDER", "").strip().lower()
    return provider if provider in SUPPORTED_IMAGE_PROVIDERS else ""


def _sanitize_prompt(prompt: str) -> str:
    normalized = re.sub(r"\s+", " ", str(prompt or "")).strip()
    return normalized[:MAX_PROMPT_CHARS]


def normalize_image_size(size: Optional[str]) -> str:
    normalized = str(size or DEFAULT_IMAGE_SIZE).strip().lower()
    if re.fullmatch(r"\d{2,4}x\d{2,4}", normalized):
        return normalized
    return DEFAULT_IMAGE_SIZE


def get_image_generation_status() -> dict[str, Any]:
    provider = _configured_provider()
    if not provider:
        status = ImageProviderStatus(
            provider="none",
            configured=False,
            available=False,
            status="not_configured",
            reason="No image generation provider is configured.",
        )
        return {
            **status.as_dict(),
            "supported_providers": list(SUPPORTED_IMAGE_PROVIDERS),
        }

    # The abstraction is ready, but concrete provider adapters are intentionally
    # not faked. A future adapter must flip this only after a real generation
    # call is implemented and verified.
    status = ImageProviderStatus(
        provider=provider,
        configured=True,
        available=False,
        status="adapter_missing",
        reason=f"{provider} is configured, but no verified image generation adapter is active yet.",
    )
    return {
        **status.as_dict(),
        "supported_providers": list(SUPPORTED_IMAGE_PROVIDERS),
    }


def generate_image(prompt: str, style: Optional[str] = None, size: Optional[str] = None) -> dict[str, Any]:
    cleaned_prompt = _sanitize_prompt(prompt)
    provider_status = get_image_generation_status()
    normalized_size = normalize_image_size(size)
    normalized_style = str(style or "").strip().lower() or None

    if not cleaned_prompt:
        return {
            "success": False,
            "status": "invalid_prompt",
            "provider": provider_status["provider"],
            "prompt": "",
            "style": normalized_style,
            "size": normalized_size,
            "message": "Please describe the image you want generated.",
            "error": "empty_prompt",
            "images": [],
        }

    if not provider_status.get("available"):
        return {
            "success": False,
            "status": provider_status.get("status") or "not_configured",
            "provider": provider_status.get("provider") or "none",
            "prompt": cleaned_prompt,
            "style": normalized_style,
            "size": normalized_size,
            "message": (
                "Image generation is not configured yet. I can prepare the prompt architecture, "
                "but I will not fake an image output."
            ),
            "error": provider_status.get("reason"),
            "images": [],
            "provider_status": provider_status,
        }

    return {
        "success": False,
        "status": "adapter_missing",
        "provider": provider_status.get("provider"),
        "prompt": cleaned_prompt,
        "style": normalized_style,
        "size": normalized_size,
        "message": "Image generation provider is configured, but the verified adapter is not implemented yet.",
        "error": "adapter_missing",
        "images": [],
        "provider_status": provider_status,
    }

