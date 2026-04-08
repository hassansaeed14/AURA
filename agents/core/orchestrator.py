from brain.intent_engine import detect_intent
from memory.vector_memory import store_memory, search_memory
from agents.memory.learning_agent import learn_from_interaction


class Orchestrator:
    def __init__(self):
        self.conversation_history = []
        self.active_agent = None
        self.last_intent = None
        self.context = {}

    # -------------------------------------
    # HISTORY
    # -------------------------------------

    def add_to_history(self, role, content, intent=None):
        self.conversation_history.append({
            "role": role,
            "content": content,
            "intent": intent
        })

        if len(self.conversation_history) > 50:
            self.conversation_history = self.conversation_history[-50:]

    def get_history(self):
        return self.conversation_history

    def get_recent_history(self, limit=10):
        return self.conversation_history[-limit:]

    def clear_history(self):
        self.conversation_history = []

    # -------------------------------------
    # CONTEXT
    # -------------------------------------

    def set_context(self, key, value):
        self.context[key] = value

    def get_context(self, key, default=None):
        return self.context.get(key, default)

    def get_all_context(self):
        return self.context

    def clear_context(self):
        self.context = {}

    # -------------------------------------
    # MEMORY
    # -------------------------------------

    def store_user_turn(self, command, intent):
        store_memory(command, {
            "type": "user_input",
            "intent": intent
        })

    def fetch_relevant_memories(self, command, limit=3):
        try:
            return search_memory(command, n_results=limit)
        except Exception as e:
            print(f"[Orchestrator Memory Error] {e}")
            return []

    def build_memory_context(self, command, limit=3):
        memories = self.fetch_relevant_memories(command, limit=limit)

        if not memories:
            return ""

        lines = []
        for memory in memories:
            text = memory.get("text", "").strip()
            if text:
                lines.append(f"- {text}")

        return "\n".join(lines)

    # -------------------------------------
    # ROUTING
    # -------------------------------------

    def route(self, command):
        intent = detect_intent(command)
        self.active_agent = intent
        self.last_intent = intent

        self.add_to_history("user", command, intent=intent)
        self.store_user_turn(command, intent)

        memory_context = self.build_memory_context(command)
        if memory_context:
            self.set_context("memory_context", memory_context)

        self.set_context("last_user_command", command)
        self.set_context("last_intent", intent)

        return intent

    # -------------------------------------
    # RESPONSE PROCESSING
    # -------------------------------------

    def process_response(self, response, intent):
        self.add_to_history("assistant", response, intent=intent)

        user_input = self.get_last_user_message()

        try:
            learn_from_interaction(user_input, response, intent)
        except Exception as e:
            print(f"[Orchestrator Learning Error] {e}")

        self.set_context("last_assistant_response", response)
        self.active_agent = intent

        return response

    # -------------------------------------
    # HELPERS
    # -------------------------------------

    def get_last_user_message(self):
        for item in reversed(self.conversation_history):
            if item["role"] == "user":
                return item["content"]
        return ""

    def get_last_assistant_message(self):
        for item in reversed(self.conversation_history):
            if item["role"] == "assistant":
                return item["content"]
        return ""

    def reset_session(self):
        self.clear_history()
        self.clear_context()
        self.active_agent = None
        self.last_intent = None


# Global orchestrator instance
orchestrator = Orchestrator()