import time
import uuid
from copy import deepcopy
from typing import Any, Dict, Optional


_LAST_TELEMETRY: Optional[Dict[str, Any]] = None


def _default_stage() -> Dict[str, Any]:
    return {
        "status": "idle",
        "time_ms": None,
    }


class ProcessingTelemetry:
    def __init__(self, message_id: Optional[str] = None) -> None:
        self.message_id = str(message_id or uuid.uuid4())
        self.request_start_time = time.perf_counter()
        self.stages: Dict[str, Dict[str, Any]] = {
            "understanding": _default_stage(),
            "intent": _default_stage(),
            "routing": _default_stage(),
            "execution": _default_stage(),
            "provider": _default_stage(),
        }

    def record_understanding(
        self,
        raw_input: str,
        normalized: str,
        entities: Dict[str, Any],
        time_ms: float,
    ) -> None:
        self.stages["understanding"] = {
            "status": "complete",
            "raw_input": raw_input,
            "normalized": normalized,
            "entities": entities,
            "time_ms": round(float(time_ms), 2),
        }

    def record_intent(
        self,
        primary_intent: str,
        confidence: float,
        alternatives: list[dict[str, Any]],
        time_ms: float,
    ) -> None:
        self.stages["intent"] = {
            "status": "complete",
            "primary_intent": primary_intent,
            "confidence": confidence,
            "alternatives": alternatives,
            "time_ms": round(float(time_ms), 2),
        }

    def record_routing(
        self,
        agent_selected: str,
        reason: str,
        trust_level: str,
        time_ms: float,
    ) -> None:
        self.stages["routing"] = {
            "status": "complete",
            "agent_selected": agent_selected,
            "reason": reason,
            "trust_level": trust_level,
            "time_ms": round(float(time_ms), 2),
        }

    def record_execution(
        self,
        agent: str,
        result: Any,
        success: bool,
        time_ms: float,
    ) -> None:
        self.stages["execution"] = {
            "status": "complete" if success else "failed",
            "agent": agent,
            "result": result,
            "success": bool(success),
            "time_ms": round(float(time_ms), 2),
        }

    def record_provider(
        self,
        provider_name: str,
        model: str,
        tokens_used: Optional[int],
        time_ms: float,
        *,
        success: bool = True,
        error: Optional[str] = None,
    ) -> None:
        self.stages["provider"] = {
            "status": "complete" if success else "failed",
            "provider_name": provider_name,
            "model": model,
            "tokens_used": tokens_used,
            "time_ms": round(float(time_ms), 2),
            "error": error,
        }

    def get_telemetry(self) -> Dict[str, Any]:
        total_time_ms = (time.perf_counter() - self.request_start_time) * 1000
        return {
            "message_id": self.message_id,
            "total_time_ms": round(total_time_ms, 2),
            "stages": deepcopy(self.stages),
        }


def set_last_telemetry(payload: Optional[Dict[str, Any] | ProcessingTelemetry]) -> None:
    global _LAST_TELEMETRY
    if payload is None:
        _LAST_TELEMETRY = None
        return
    if isinstance(payload, ProcessingTelemetry):
        _LAST_TELEMETRY = payload.get_telemetry()
        return
    _LAST_TELEMETRY = deepcopy(payload)


def get_last_telemetry() -> Optional[Dict[str, Any]]:
    if _LAST_TELEMETRY is None:
        return None
    return deepcopy(_LAST_TELEMETRY)
