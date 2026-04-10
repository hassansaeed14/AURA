from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, List, Optional, Tuple

from agents.registry import get_agent_descriptor


@dataclass(frozen=True)
class AgentRoute:
    intent: str
    agent: str
    supported_actions: Tuple[str, ...]
    capability_mode: str
    trust_level: str
    required_inputs: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


def _route(
    intent: str,
    agent: str,
    supported_actions: Tuple[str, ...],
    *,
    required_inputs: Tuple[str, ...] = (),
) -> AgentRoute:
    descriptor = get_agent_descriptor(agent)
    capability_mode = descriptor.capability_mode if descriptor else "hybrid"
    trust_level = descriptor.trust_level if descriptor else "safe"
    return AgentRoute(
        intent=intent,
        agent=agent,
        supported_actions=supported_actions,
        capability_mode=capability_mode,
        trust_level=trust_level,
        required_inputs=required_inputs,
    )


ROUTES: Tuple[AgentRoute, ...] = (
    _route("general", "general", ("respond",)),
    _route("greeting", "general", ("greet",)),
    _route("identity", "identity", ("identify",)),
    _route("time", "general", ("time_read",)),
    _route("date", "general", ("date_read",)),
    _route("weather", "weather", ("weather_read",), required_inputs=("topic",)),
    _route("news", "news", ("news_read",), required_inputs=("topic",)),
    _route("math", "math", ("math_solve",), required_inputs=("amounts",)),
    _route("translation", "translation", ("translate",), required_inputs=("languages",)),
    _route("research", "research", ("research",), required_inputs=("topic",)),
    _route("study", "study", ("teach",), required_inputs=("topic",)),
    _route("code", "code", ("code_help",), required_inputs=("topic",)),
    _route("content", "content", ("write_content",), required_inputs=("topic",)),
    _route("email", "email", ("write_email",), required_inputs=("topic",)),
    _route("summarize", "summarize", ("summarize",), required_inputs=("topic",)),
    _route("grammar", "grammar", ("proofread",), required_inputs=("topic",)),
    _route("quiz", "quiz", ("quiz_create",), required_inputs=("topic",)),
    _route("dictionary", "dictionary", ("define",), required_inputs=("topic",)),
    _route("synonyms", "dictionary", ("synonyms",), required_inputs=("topic",)),
    _route("web_search", "web_search", ("web_search",), required_inputs=("topic",)),
    _route("youtube", "youtube", ("video_search",), required_inputs=("topic",)),
    _route("currency", "currency", ("convert_currency",), required_inputs=("amounts", "currencies")),
    _route("crypto", "currency", ("crypto_lookup",), required_inputs=("currencies",)),
    _route("joke", "joke", ("tell_joke",)),
    _route("quote", "quote", ("quote_read",)),
    _route("file", "file", ("file_read",), required_inputs=("files",)),
    _route("list_files", "list_files", ("file_list",)),
    _route("screenshot", "screenshot", ("screenshot",)),
    _route("task", "task", ("task_read", "task_add", "task_complete", "task_delete", "task_plan")),
    _route("reminder", "reminder", ("reminder_read", "reminder_add", "reminder_complete", "reminder_delete")),
    _route("compare", "compare", ("compare",), required_inputs=("topic",)),
    _route("reasoning", "reasoning", ("reason",), required_inputs=("topic",)),
    _route("insights", "insights", ("insights_read",)),
    _route("memory", "learning", ("memory_read", "memory_write")),
    _route("fitness", "fitness", ("fitness_plan",), required_inputs=("topic",)),
    _route("password", "password", ("password_generate", "password_validate")),
    _route("purchase", "permission", ("purchase_request",), required_inputs=("topic", "amounts")),
)

ROUTE_MAP: Dict[str, AgentRoute] = {route.intent: route for route in ROUTES}


def get_agent_route(intent: str | None) -> Optional[AgentRoute]:
    normalized = str(intent or "").strip().lower()
    return ROUTE_MAP.get(normalized)


def list_agent_routes() -> List[Dict[str, object]]:
    return [route.to_dict() for route in ROUTES]


def list_actions_for_agent(agent: str | None) -> List[str]:
    normalized = str(agent or "").strip().lower()
    actions = []
    for route in ROUTES:
        if route.agent != normalized:
            continue
        for action_name in route.supported_actions:
            if action_name not in actions:
                actions.append(action_name)
    return actions
