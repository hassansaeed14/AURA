from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, List, Optional, Tuple

from agents.registry import get_agent_descriptor
from config.agent_registry import ROUTES, get_agent_route


@dataclass(frozen=True)
class CapabilityRecord:
    intent: str
    agent: str
    agent_name: str
    supported_actions: Tuple[str, ...]
    capability_mode: str
    trust_level: str
    required_inputs: Tuple[str, ...]
    execution_path: str
    status: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


def _build_record(intent: str) -> CapabilityRecord:
    route = get_agent_route(intent)
    if route is None:
        raise KeyError(f"Unknown intent: {intent}")

    descriptor = get_agent_descriptor(route.agent)
    return CapabilityRecord(
        intent=route.intent,
        agent=route.agent,
        agent_name=descriptor.name if descriptor else route.agent.replace("_", " ").title(),
        supported_actions=route.supported_actions,
        capability_mode=route.capability_mode,
        trust_level=route.trust_level,
        required_inputs=route.required_inputs,
        execution_path=descriptor.integration_path if descriptor else "Runtime routing",
        status=descriptor.status if descriptor else "live",
    )


CAPABILITY_REGISTRY: Dict[str, CapabilityRecord] = {
    route.intent: _build_record(route.intent)
    for route in ROUTES
}


def get_capability(intent_or_agent: str | None) -> Optional[CapabilityRecord]:
    normalized = str(intent_or_agent or "").strip().lower()
    if not normalized:
        return None

    if normalized in CAPABILITY_REGISTRY:
        return CAPABILITY_REGISTRY[normalized]

    for record in CAPABILITY_REGISTRY.values():
        if record.agent == normalized:
            return record

    return None


def list_capabilities(*, include_placeholders: bool = True) -> List[Dict[str, object]]:
    records = []
    for record in CAPABILITY_REGISTRY.values():
        if not include_placeholders and record.capability_mode == "placeholder":
            continue
        records.append(record.to_dict())
    return records


def capability_exists(intent_or_agent: str | None) -> bool:
    return get_capability(intent_or_agent) is not None


def supports_action(intent_or_agent: str | None, action_name: str | None) -> bool:
    record = get_capability(intent_or_agent)
    if record is None:
        return False
    normalized = str(action_name or "").strip().lower()
    return normalized in record.supported_actions


def summarize_capabilities() -> Dict[str, object]:
    summary = {
        "total": 0,
        "modes": {"real": 0, "hybrid": 0, "placeholder": 0},
        "trust_levels": {"safe": 0, "private": 0, "sensitive": 0, "critical": 0},
    }

    for record in CAPABILITY_REGISTRY.values():
        summary["total"] += 1
        summary["modes"][record.capability_mode] = summary["modes"].get(record.capability_mode, 0) + 1
        summary["trust_levels"][record.trust_level] = summary["trust_levels"].get(record.trust_level, 0) + 1

    return summary
