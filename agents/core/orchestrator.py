from brain.intent_engine import detect_intent
from memory.vector_memory import store_memory, search_memory
from agents.memory.learning_agent import learn_from_interaction

class Orchestrator:
    def __init__(self):
        self.conversation_history = []
        self.active_agent = None
        self.context = {}

    def add_to_history(self, role, content):
        self.conversation_history.append({
            "role": role,
            "content": content
        })
        if len(self.conversation_history) > 50:
            self.conversation_history.pop(0)

    def get_history(self):
        return self.conversation_history

    def set_context(self, key, value):
        self.context[key] = value

    def get_context(self, key):
        return self.context.get(key, None)

    def clear_context(self):
        self.context = {}

    def route(self, command):
        intent = detect_intent(command)
        self.active_agent = intent
        self.add_to_history("user", command)
        store_memory(command, {"type": "user_input", "intent": intent})
        return intent

    def process_response(self, response, intent):
        self.add_to_history("assistant", response)
        learn_from_interaction(
            self.conversation_history[-2]["content"] if len(self.conversation_history) >= 2 else "",
            response,
            intent
        )
        return response

# Global orchestrator instance
orchestrator = Orchestrator()