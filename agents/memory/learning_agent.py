import json
import os
import datetime
from groq import Groq
from config.settings import GROQ_API_KEY, MODEL_NAME
from memory.vector_memory import store_memory, search_memory

client = Groq(api_key=GROQ_API_KEY)

LEARNING_FILE = "memory/aura_learning.json"

def load_learning_data():
    if not os.path.exists(LEARNING_FILE):
        return {
            "user_preferences": {},
            "frequent_topics": {},
            "interaction_patterns": [],
            "learned_facts": []
        }
    with open(LEARNING_FILE, 'r') as f:
        return json.load(f)

def save_learning_data(data):
    with open(LEARNING_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def learn_from_interaction(user_input, aura_response, intent):
    data = load_learning_data()
    
    # Track frequent topics
    if intent not in ["greeting", "shutdown", "time", "date"]:
        if intent in data["frequent_topics"]:
            data["frequent_topics"][intent] += 1
        else:
            data["frequent_topics"][intent] = 1
    
    # Store interaction pattern
    data["interaction_patterns"].append({
        "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "intent": intent,
        "input_length": len(user_input)
    })
    
    # Keep only last 100 patterns
    if len(data["interaction_patterns"]) > 100:
        data["interaction_patterns"] = data["interaction_patterns"][-100:]
    
    save_learning_data(data)
    
    # Store in vector memory for semantic search
    store_memory(
        f"User asked about {intent}: {user_input[:100]}",
        {"type": "interaction", "intent": intent}
    )

def get_user_insights():
    data = load_learning_data()
    
    if not data["frequent_topics"]:
        return "I am still learning about your preferences. Keep talking to me!"
    
    sorted_topics = sorted(
        data["frequent_topics"].items(),
        key=lambda x: x[1],
        reverse=True
    )
    
    result = "AURA LEARNING INSIGHTS\n\n"
    result += "YOUR MOST USED FEATURES:\n"
    for i, (topic, count) in enumerate(sorted_topics[:5], 1):
        result += f"{i}. {topic.title()} — used {count} times\n"
    
    result += f"\nTOTAL INTERACTIONS: {len(data['interaction_patterns'])}\n"
    
    # Get favorite time
    if data["interaction_patterns"]:
        hours = [int(p["time"].split(" ")[1].split(":")[0])
                for p in data["interaction_patterns"]]
        avg_hour = sum(hours) // len(hours)
        period = "morning" if avg_hour < 12 else "afternoon" if avg_hour < 17 else "evening"
        result += f"YOU MOSTLY USE AURA IN THE: {period.upper()}\n"
    
    return result

def learn_user_preference(key, value):
    data = load_learning_data()
    data["user_preferences"][key] = value
    save_learning_data(data)
    return f"Got it! I learned that you prefer {key}: {value}"

def get_personalized_greeting():
    data = load_learning_data()
    
    if not data["frequent_topics"]:
        return None
    
    sorted_topics = sorted(
        data["frequent_topics"].items(),
        key=lambda x: x[1],
        reverse=True
    )
    
    top_topic = sorted_topics[0][0] if sorted_topics else None
    
    if top_topic:
        return f"Welcome back! Ready to help you with {top_topic} today?"
    return None