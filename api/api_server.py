import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import uvicorn


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = PROJECT_ROOT / "interface" / "web"
APP_HTML = WEB_DIR / "aura.html"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.registry import get_agent_summary, list_agents
from agents.agent_fabric import list_generated_agent_cards, run_generated_agent
from brain.capability_registry import list_capabilities, summarize_capabilities
from brain.core_ai import process_command_detailed
from brain.provider_hub import summarize_provider_statuses
from config.master_spec import CAPABILITY_LABELS, HYBRID_IMPLEMENTATION_ORDER
from config.system_modes import list_system_modes
from config.settings import MODEL_NAME
from memory import vector_memory
from memory.memory_manager import save_chat, load_chat_history
from memory.memory_stats import get_memory_stats
from security.auth_manager import get_auth_state
from security.lock_manager import is_locked, lock_resource, unlock_resource
from security.pin_manager import get_pin_status
from security.session_manager import approve_action
from api.auth import register_user, login_user, get_user
from voice.voice_controller import (
    get_voice_status,
    speak_response,
    stop_voice_output,
    transcribe_microphone_request,
    update_voice_preferences,
)
from voice.voice_pipeline import process_voice_text


app = FastAPI()

app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")


class Command(BaseModel):
    text: str
    username: str = "guest"


class LoginData(BaseModel):
    username: str
    password: str


class RegisterData(BaseModel):
    username: str
    password: str
    name: str


class TaskCreate(BaseModel):
    text: str
    priority: str = "medium"
    due_date: Optional[str] = None


class TaskUpdate(BaseModel):
    text: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[str] = None
    done: Optional[bool] = None


class ReminderCreate(BaseModel):
    text: str
    date: Optional[str] = None
    time: Optional[str] = None


class ReminderUpdate(BaseModel):
    text: Optional[str] = None
    date: Optional[str] = None
    time: Optional[str] = None
    status: Optional[str] = None


class AgentRunRequest(BaseModel):
    text: str
    username: str = "guest"
    session_id: str = "default"
    confirmed: bool = False
    pin: Optional[str] = None
    save_artifact: Optional[bool] = None


class VoiceTextRequest(BaseModel):
    text: str


class VoiceCaptureRequest(BaseModel):
    timeout: int = 5
    phrase_time_limit: Optional[int] = None


class VoiceSettingsUpdate(BaseModel):
    persona: Optional[str] = None
    language: Optional[str] = None
    voice_gender: Optional[str] = None
    rate: Optional[float] = None
    volume: Optional[float] = None
    enabled: Optional[bool] = None


class SecurityActionRequest(BaseModel):
    action_name: str
    session_id: str = "default"


class LockRequest(BaseModel):
    resource_id: str
    owner: Optional[str] = None


TASKS_FILE = PROJECT_ROOT / "memory" / "tasks.json"
REMINDERS_FILE = PROJECT_ROOT / "memory" / "reminders.json"
USER_MEMORY_FILE = PROJECT_ROOT / "memory" / "user_memory.json"
LEARNING_FILE = PROJECT_ROOT / "memory" / "aura_learning.json"
IMPROVEMENT_FILE = PROJECT_ROOT / "memory" / "aura_improvement_log.json"
PERMISSIONS_FILE = PROJECT_ROOT / "memory" / "permissions.json"
VOICE_SETTINGS_FILE = PROJECT_ROOT / "memory" / "voice_settings.json"


def _now_string() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def _read_json_list(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8") as file:
            payload = json.load(file)
        return payload if isinstance(payload, list) else []
    except Exception:
        return []


def _read_json_object(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as file:
            payload = json.load(file)
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _write_json_list(path: Path, items: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(items, file, indent=2, ensure_ascii=False)


def _next_id(items: list[dict[str, Any]]) -> int:
    return max((int(item.get("id", 0)) for item in items), default=0) + 1


def _task_summary(tasks: list[dict[str, Any]]) -> dict[str, int]:
    pending = sum(1 for task in tasks if task.get("status") != "completed")
    completed = sum(1 for task in tasks if task.get("status") == "completed")
    return {
        "total": len(tasks),
        "pending": pending,
        "completed": completed,
    }


def _reminder_summary(reminders: list[dict[str, Any]]) -> dict[str, int]:
    active = sum(1 for reminder in reminders if reminder.get("status", "active") == "active")
    completed = sum(1 for reminder in reminders if reminder.get("status") == "completed")
    return {
        "total": len(reminders),
        "active": active,
        "completed": completed,
    }


def _build_personalized_greeting(user_name: str | None) -> str:
    if user_name:
        return f"Welcome back, {user_name}. AURA is ready."
    return "Hello. AURA is ready."


def _normalize_name(*values: Any) -> Optional[str]:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text.title()
    return None


@app.get("/", response_class=HTMLResponse)
async def home():
    with open(APP_HTML, "r", encoding="utf-8") as f:
        return f.read()


@app.get("/login", response_class=HTMLResponse)
async def login_page():
    with open(WEB_DIR / "login.html", "r", encoding="utf-8") as f:
        return f.read()


@app.get("/register", response_class=HTMLResponse)
async def register_page():
    with open(WEB_DIR / "register.html", "r", encoding="utf-8") as f:
        return f.read()


@app.post("/api/login")
async def login(data: LoginData):
    success, result = login_user(data.username, data.password)
    if success:
        return {"success": True, "user": result}
    raise HTTPException(status_code=401, detail=result)


@app.post("/api/register")
async def register(data: RegisterData):
    success, message = register_user(data.username, data.password, data.name)
    if success:
        return {"success": True, "message": message}
    raise HTTPException(status_code=400, detail=message)


@app.post("/chat")
async def chat(command: Command):
    try:
        result = process_command_detailed(command.text)
        response = result["response"]

        save_chat(command.text, response)

        return {
            "intent": result["intent"],
            "detected_intent": result["detected_intent"],
            "confidence": round(result["confidence"], 2),
            "response": response,
            "username": command.username,
            "plan": result.get("plan", []),
            "used_agents": result.get("used_agents", []),
            "agent_capabilities": result.get("agent_capabilities", []),
            "execution_mode": result.get("execution_mode"),
            "decision": result.get("decision", {}),
            "orchestration": result.get("orchestration", {}),
            "permission_action": result.get("permission_action"),
            "permission": result.get("permission", {}),
        }

    except Exception as e:
        return {
            "intent": "error",
            "detected_intent": "error",
            "confidence": 0.0,
            "response": f"Sorry, I encountered an error: {str(e)}",
            "username": command.username,
            "plan": [],
            "used_agents": [],
            "agent_capabilities": [],
            "execution_mode": "error",
            "decision": {},
            "orchestration": {},
            "permission_action": None,
            "permission": {},
        }


@app.get("/history")
async def history():
    return load_chat_history()


@app.get("/api/user/{username}")
async def get_user_info(username: str):
    user = get_user(username)
    if user:
        return {"success": True, "user": user}
    raise HTTPException(status_code=404, detail="User not found")


@app.get("/api/memory/insights")
async def get_memory_insights(username: str = "guest"):
    user = get_user(username) or {}
    explicit_memory = _read_json_object(USER_MEMORY_FILE)
    learning = _read_json_object(LEARNING_FILE)

    user_profile = learning.get("user_profile", {})
    preferences = user_profile.get("preferences") or learning.get("user_preferences") or {}
    interests = user_profile.get("interests") or []
    learned_facts = learning.get("learned_facts") or []
    topic_frequency = learning.get("topic_frequency") or learning.get("frequent_topics") or {}
    top_intents = sorted(topic_frequency.items(), key=lambda item: item[1], reverse=True)[:6]

    remembered_name = _normalize_name(
        user.get("name"),
        explicit_memory.get("user_name"),
        user_profile.get("name"),
    )
    profile_name = remembered_name or "Guest"

    return {
        "mode": "hybrid",
        "remembered_name": profile_name,
        "greeting_preview": _build_personalized_greeting(remembered_name),
        "profile": {
            "name": profile_name,
            "plan": user.get("plan", "free"),
            "created": user.get("created"),
            "city": explicit_memory.get("user_city"),
            "age": explicit_memory.get("user_age"),
        },
        "preferences": preferences,
        "interests": interests,
        "learned_facts": learned_facts,
        "top_intents": [
            {"intent": intent, "count": count}
            for intent, count in top_intents
        ],
        "insights": [
            f"Top intent right now is {top_intents[0][0]}." if top_intents else "AURA is still learning your recurring intent patterns.",
            "Stored facts come from explicit memory and interaction learning.",
            "Preferences are limited until more real UI controls are connected.",
        ],
        "sources": {
            "explicit_memory": str(USER_MEMORY_FILE.relative_to(PROJECT_ROOT)),
            "learning": str(LEARNING_FILE.relative_to(PROJECT_ROOT)),
        },
    }


@app.get("/api/intelligence/insights")
async def get_intelligence_insights():
    improvement = _read_json_object(IMPROVEMENT_FILE)
    permissions = _read_json_object(PERMISSIONS_FILE)
    voice = _read_json_object(VOICE_SETTINGS_FILE)

    failures = improvement.get("failures") or []
    low_confidence = improvement.get("low_confidence_commands") or []
    suggestions = improvement.get("improvement_suggestions") or []

    return {
        "mode": "hybrid",
        "reasoning_status": "available",
        "low_confidence_count": len(low_confidence),
        "failure_count": len(failures),
        "recent_low_confidence": low_confidence[-6:],
        "recent_failures": failures[-6:],
        "improvement_suggestions": suggestions[-6:],
        "permissions": permissions,
        "voice": voice,
        "sources": {
            "improvement_log": str(IMPROVEMENT_FILE.relative_to(PROJECT_ROOT)),
            "permissions": str(PERMISSIONS_FILE.relative_to(PROJECT_ROOT)),
            "voice": str(VOICE_SETTINGS_FILE.relative_to(PROJECT_ROOT)),
        },
    }


@app.get("/api/tasks")
async def get_tasks():
    tasks = _read_json_list(TASKS_FILE)
    tasks.sort(key=lambda item: (item.get("status") == "completed", -int(item.get("id", 0))))
    return {
        "items": tasks,
        "summary": _task_summary(tasks),
        "mode": "real",
        "source": str(TASKS_FILE.relative_to(PROJECT_ROOT)),
    }


@app.post("/api/tasks")
async def create_task(task: TaskCreate):
    text = task.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Task text is required")

    tasks = _read_json_list(TASKS_FILE)
    item = {
        "id": _next_id(tasks),
        "task": text,
        "priority": (task.priority or "medium").strip().lower() or "medium",
        "due_date": task.due_date.strip() if task.due_date else None,
        "status": "pending",
        "created": _now_string(),
    }
    tasks.append(item)
    _write_json_list(TASKS_FILE, tasks)
    return {
        "success": True,
        "item": item,
        "summary": _task_summary(tasks),
    }


@app.patch("/api/tasks/{task_id}")
async def update_task(task_id: int, task: TaskUpdate):
    tasks = _read_json_list(TASKS_FILE)
    item = next((entry for entry in tasks if int(entry.get("id", 0)) == task_id), None)
    if item is None:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.text is not None:
        text = task.text.strip()
        if not text:
            raise HTTPException(status_code=400, detail="Task text is required")
        item["task"] = text

    if task.priority is not None:
        item["priority"] = task.priority.strip().lower() or "medium"

    if task.due_date is not None:
        item["due_date"] = task.due_date.strip() or None

    if task.done is not None:
        if task.done:
            item["status"] = "completed"
            item["completed_at"] = _now_string()
        else:
            item["status"] = "pending"
            item.pop("completed_at", None)

    _write_json_list(TASKS_FILE, tasks)
    return {
        "success": True,
        "item": item,
        "summary": _task_summary(tasks),
    }


@app.delete("/api/tasks/{task_id}")
async def delete_task(task_id: int):
    tasks = _read_json_list(TASKS_FILE)
    updated = [entry for entry in tasks if int(entry.get("id", 0)) != task_id]
    if len(updated) == len(tasks):
        raise HTTPException(status_code=404, detail="Task not found")
    _write_json_list(TASKS_FILE, updated)
    return {
        "success": True,
        "summary": _task_summary(updated),
    }


@app.get("/api/reminders")
async def get_reminders():
    reminders = _read_json_list(REMINDERS_FILE)
    reminders.sort(key=lambda item: (item.get("status") == "completed", -int(item.get("id", 0))))
    return {
        "items": reminders,
        "summary": _reminder_summary(reminders),
        "mode": "real",
        "source": str(REMINDERS_FILE.relative_to(PROJECT_ROOT)),
    }


@app.post("/api/reminders")
async def create_reminder(reminder: ReminderCreate):
    text = reminder.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Reminder text is required")

    reminders = _read_json_list(REMINDERS_FILE)
    item = {
        "id": _next_id(reminders),
        "text": text,
        "time": reminder.time.strip() if reminder.time else None,
        "date": reminder.date.strip() if reminder.date else None,
        "created": _now_string(),
        "status": "active",
        "completed_at": None,
    }
    reminders.append(item)
    _write_json_list(REMINDERS_FILE, reminders)
    return {
        "success": True,
        "item": item,
        "summary": _reminder_summary(reminders),
    }


@app.patch("/api/reminders/{reminder_id}")
async def update_reminder(reminder_id: int, reminder: ReminderUpdate):
    reminders = _read_json_list(REMINDERS_FILE)
    item = next((entry for entry in reminders if int(entry.get("id", 0)) == reminder_id), None)
    if item is None:
        raise HTTPException(status_code=404, detail="Reminder not found")

    if reminder.text is not None:
        text = reminder.text.strip()
        if not text:
            raise HTTPException(status_code=400, detail="Reminder text is required")
        item["text"] = text

    if reminder.date is not None:
        item["date"] = reminder.date.strip() or None

    if reminder.time is not None:
        item["time"] = reminder.time.strip() or None

    if reminder.status is not None:
        status = reminder.status.strip().lower()
        if status not in {"active", "completed"}:
            raise HTTPException(status_code=400, detail="Reminder status must be active or completed")
        item["status"] = status
        item["completed_at"] = _now_string() if status == "completed" else None

    _write_json_list(REMINDERS_FILE, reminders)
    return {
        "success": True,
        "item": item,
        "summary": _reminder_summary(reminders),
    }


@app.delete("/api/reminders/{reminder_id}")
async def delete_reminder(reminder_id: int):
    reminders = _read_json_list(REMINDERS_FILE)
    updated = [entry for entry in reminders if int(entry.get("id", 0)) != reminder_id]
    if len(updated) == len(reminders):
        raise HTTPException(status_code=404, detail="Reminder not found")
    _write_json_list(REMINDERS_FILE, updated)
    return {
        "success": True,
        "summary": _reminder_summary(updated),
    }


@app.get("/api/system/status")
async def system_status():
    summary = get_agent_summary()
    memory_status = vector_memory.get_status()
    memory_connected = memory_status["vector_store_ready"]
    memory_health = "connected" if memory_connected else "degraded"
    memory_mode = "real" if memory_connected else "fallback"
    provider_summary = summarize_provider_statuses()
    return {
        "status": "online",
        "version": "1.0.0",
        "model": MODEL_NAME,
        "orchestrator": "rule_based_available",
        "reasoning": "hybrid_available",
        "memory": memory_health,
        "planner": "hybrid_available",
        "agents": summary,
        "capability_summary": summary.get("capability_modes", {}),
        "brain_capabilities": summarize_capabilities(),
        "memory_stats": get_memory_stats(),
        "memory_backend": memory_status,
        "providers": provider_summary,
        "security": {"pin": get_pin_status()},
        "subsystems": {
            "orchestrator": {"status": "available", "mode": "real", "source": "rule_based"},
            "reasoning": {"status": "available", "mode": "hybrid"},
            "planner": {"status": "available", "mode": "hybrid"},
            "voice": {"status": "available" if get_voice_status()["settings"]["enabled"] else "standby", "mode": "hybrid"},
            "providers": {
                "status": "available" if provider_summary["available"] else "degraded",
                "mode": "hybrid",
                "available": provider_summary["available"],
            },
            "memory": {
                "status": memory_health,
                "mode": memory_mode,
                "vector_store_ready": memory_connected,
                "backend": memory_status["backend"],
                "last_error": memory_status["last_error"],
            },
        },
        "implementation_doctrine": {
            "capability_labels": list(CAPABILITY_LABELS),
            "hybrid_order": list(HYBRID_IMPLEMENTATION_ORDER),
            "implementation_priority": list(CAPABILITY_LABELS),
        },
    }


@app.get("/api/agents")
async def get_agents():
    return {
        "agents": list_agents(),
        "generated_agents": list_generated_agent_cards(),
        "providers": summarize_provider_statuses(),
        "summary": get_agent_summary(),
        "doctrine": {
            "capability_labels": list(CAPABILITY_LABELS),
            "hybrid_order": list(HYBRID_IMPLEMENTATION_ORDER),
            "implementation_priority": list(CAPABILITY_LABELS),
        },
    }


@app.get("/api/capabilities")
async def get_capabilities():
    return {
        "items": list_capabilities(),
        "summary": summarize_capabilities(),
    }


@app.get("/api/providers")
async def get_provider_status():
    return summarize_provider_statuses()


@app.get("/api/memory/stats")
async def get_memory_status():
    return get_memory_stats()


@app.get("/api/security/status")
async def get_security_status(username: str = "guest", session_id: str = "default", resource_id: Optional[str] = None):
    return {
        "pin": get_pin_status(),
        "auth": get_auth_state(username),
        "session_id": session_id,
        "resource_locked": is_locked(resource_id) if resource_id else False,
    }


@app.get("/api/system/modes")
async def get_modes():
    return {
        "items": list_system_modes(),
    }

    if False:  # Legacy static catalog kept only as migration reference.
        return {
        "agents": [
            {"id": "general", "name": "General AURA", "icon": "🤖", "description": "General AI assistant"},
            {"id": "study", "name": "Study Agent", "icon": "📚", "description": "Learn any topic"},
            {"id": "research", "name": "Research Agent", "icon": "🔍", "description": "Deep research"},
            {"id": "code", "name": "Coding Agent", "icon": "💻", "description": "Programming help"},
            {"id": "weather", "name": "Weather Agent", "icon": "🌤️", "description": "Weather info"},
            {"id": "news", "name": "News Agent", "icon": "📰", "description": "Latest news"},
            {"id": "math", "name": "Math Agent", "icon": "🧮", "description": "Math solver"},
            {"id": "translation", "name": "Translation Agent", "icon": "🌍", "description": "Translate languages"},
            {"id": "email", "name": "Email Writer", "icon": "📧", "description": "Write emails"},
            {"id": "content", "name": "Content Writer", "icon": "✍️", "description": "Write content"},
            {"id": "summarize", "name": "Summarizer", "icon": "📝", "description": "Summarize text"},
            {"id": "grammar", "name": "Grammar Check", "icon": "✅", "description": "Fix grammar"},
            {"id": "quiz", "name": "Quiz Agent", "icon": "🎯", "description": "Generate quizzes"},
            {"id": "joke", "name": "Joke Agent", "icon": "😄", "description": "Tell jokes"},
            {"id": "quote", "name": "Quote Agent", "icon": "💭", "description": "Inspiring quotes"},
            {"id": "password", "name": "Password Agent", "icon": "🔐", "description": "Generate passwords"},
            {"id": "task", "name": "Task Manager", "icon": "📋", "description": "Manage tasks"},
            {"id": "reminder", "name": "Reminder Agent", "icon": "⏰", "description": "Set reminders"},
            {"id": "resume", "name": "Resume Builder", "icon": "📄", "description": "Build resume"},
            {"id": "currency", "name": "Currency Agent", "icon": "💱", "description": "Convert currency"},
            {"id": "dictionary", "name": "Dictionary", "icon": "📖", "description": "Define words"},
            {"id": "youtube", "name": "YouTube Agent", "icon": "▶️", "description": "YouTube search"},
            {"id": "web_search", "name": "Web Search", "icon": "🌐", "description": "Search web"},
            {"id": "file", "name": "File Agent", "icon": "📁", "description": "Read files"},
            {"id": "screenshot", "name": "Screenshot", "icon": "📸", "description": "Take screenshots"},
            {"id": "fitness", "name": "Fitness Agent", "icon": "💪", "description": "Workout and fitness plans"}
        ]
    }


@app.post("/api/agents/run/{agent_id}")
async def run_agent_endpoint(agent_id: str, request: AgentRunRequest):
    generated_ids = {item["id"] for item in list_generated_agent_cards()}
    if agent_id in generated_ids:
        result = run_generated_agent(
            agent_id,
            request.text,
            username=request.username,
            session_id=request.session_id,
            confirmed=request.confirmed,
            pin=request.pin,
            save_artifact=request.save_artifact,
        )
        return {
            "success": bool(result.get("success")),
            "dispatch_mode": "generated_agent",
            "agent_id": agent_id,
            "result": result,
        }

    runtime_result = process_command_detailed(request.text)
    matched_target = (
        agent_id == runtime_result.get("intent")
        or agent_id == runtime_result.get("detected_intent")
        or agent_id in runtime_result.get("used_agents", [])
    )
    return {
        "success": True,
        "dispatch_mode": "runtime_route",
        "agent_id": agent_id,
        "matched_target": matched_target,
        "result": runtime_result,
    }


@app.get("/api/voice/status")
async def get_voice_runtime_status():
    return get_voice_status()


@app.patch("/api/voice/settings")
async def update_voice_settings_endpoint(settings: VoiceSettingsUpdate):
    return update_voice_preferences(**settings.model_dump(exclude_none=True))


@app.post("/api/voice/text")
async def process_voice_text_endpoint(request: VoiceTextRequest):
    return process_voice_text(request.text)


@app.post("/api/voice/speak")
async def speak_voice_text_endpoint(request: VoiceTextRequest):
    return speak_response(request.text)


@app.post("/api/voice/stop")
async def stop_voice_text_endpoint():
    return stop_voice_output()


@app.post("/api/voice/microphone")
async def transcribe_voice_microphone_endpoint(request: VoiceCaptureRequest):
    return transcribe_microphone_request(timeout=request.timeout, phrase_time_limit=request.phrase_time_limit)


@app.post("/api/security/session-approve")
async def approve_security_action(request: SecurityActionRequest):
    return approve_action(request.session_id, request.action_name)


@app.post("/api/security/lock")
async def lock_resource_endpoint(request: LockRequest):
    return lock_resource(request.resource_id, owner=request.owner)


@app.post("/api/security/unlock")
async def unlock_resource_endpoint(request: LockRequest):
    return unlock_resource(request.resource_id)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
