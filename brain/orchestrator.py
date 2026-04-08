from groq import Groq
from config.settings import GROQ_API_KEY, MODEL_NAME
from memory.vector_memory import store_memory, search_memory
from memory.knowledge_base import get_user_name, get_user_city
import json
import re

client = Groq(api_key=GROQ_API_KEY)

class MasterOrchestrator:
    
    def __init__(self):
        self.conversation_history = []
        self.active_agents = []
        self.context = {}
    
    def analyze_task(self, command):
        # Ask AI to analyze what agents are needed
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a task analyzer for AURA AI system. "
                        "Analyze the user command and determine which agents are needed. "
                        "Available agents: weather, news, math, translation, email, "
                        "content, web_search, study, research, code, memory, general. "
                        "Respond with JSON only like this:\n"
                        '{"primary_agent": "agent_name", '
                        '"secondary_agents": ["agent1", "agent2"], '
                        '"requires_multiple": true/false, '
                        '"task_description": "brief description"}'
                    )
                },
                {
                    "role": "user",
                    "content": f"Analyze this command: {command}"
                }
            ],
            max_tokens=200
        )
        
        try:
            text = response.choices[0].message.content
            # Extract JSON
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
        
        return {
            "primary_agent": "general",
            "secondary_agents": [],
            "requires_multiple": False,
            "task_description": command
        }
    
    def add_to_history(self, role, content):
        self.conversation_history.append({
            "role": role,
            "content": content
        })
        if len(self.conversation_history) > 20:
            self.conversation_history.pop(0)
    
    def get_context(self):
        name = get_user_name()
        city = get_user_city()
        context = ""
        if name:
            context += f"User name: {name}. "
        if city:
            context += f"User city: {city}. "
        return context
    
    def synthesize_responses(self, command, agent_responses):
        # If multiple agents used, synthesize into one perfect response
        if len(agent_responses) == 1:
            return list(agent_responses.values())[0]
        
        combined = "\n\n".join([
            f"{agent.upper()} DATA:\n{response}"
            for agent, response in agent_responses.items()
        ])
        
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are AURA Master Synthesizer. "
                        "Multiple agents have provided data. "
                        "Synthesize all this data into ONE perfect, "
                        "coherent and helpful response for the user. "
                        "Make it natural and flowing. "
                        "No markdown symbols."
                    )
                },
                {
                    "role": "user",
                    "content": (
                        f"User asked: {command}\n\n"
                        f"Agent responses:\n{combined}\n\n"
                        "Synthesize into one perfect response."
                    )
                }
            ],
            max_tokens=1500
        )
        return response.choices[0].message.content

# Global orchestrator instance
orchestrator = MasterOrchestrator()