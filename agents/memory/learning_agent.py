import json
import os
import datetime
from collections import Counter
from memory.vector_memory import store_memory, search_memory

LEARNING_FILE = "memory/aura_learning.json"


# --------------------------------------------------
# INITIAL DATA STRUCTURE
# --------------------------------------------------

def initialize_learning_data():
    return {
        "user_profile": {
            "name": None,
            "interests": [],
            "preferences": {}
        },
        "topic_frequency": {},
        "interaction_history": [],
        "behavior_stats": {
            "short_queries": 0,
            "medium_queries": 0,
            "long_queries": 0
        },
        "learned_facts": [],
        "intent_sequences": [],
        "intent_weights": {},
        "last_seen": None
    }


# --------------------------------------------------
# LOAD / SAVE (AUTO-REPAIR SAFE)
# --------------------------------------------------

def load_data():

    if not os.path.exists(LEARNING_FILE):
        return initialize_learning_data()

    with open(LEARNING_FILE, "r") as f:
        data = json.load(f)

    # 🔥 AUTO-REPAIR
    default = initialize_learning_data()

    def merge(d, default_d):
        for key, value in default_d.items():
            if key not in d:
                d[key] = value
            elif isinstance(value, dict):
                merge(d[key], value)

    merge(data, default)

    return data


def save_data(data):
    with open(LEARNING_FILE, "w") as f:
        json.dump(data, f, indent=4)


# --------------------------------------------------
# QUERY LENGTH ANALYSIS
# --------------------------------------------------

def analyze_query_length(text):
    words = len(text.split())

    if words < 5:
        return "short"
    elif words < 15:
        return "medium"
    else:
        return "long"


# --------------------------------------------------
# FACT EXTRACTION
# --------------------------------------------------

def extract_fact(user_input):
    text = user_input.lower()

    patterns = [
        "my favorite",
        "i like",
        "i love",
        "i prefer",
        "my name is",
        "i usually",
        "i hate"
    ]

    for p in patterns:
        if p in text:
            return user_input.strip()

    return None


# --------------------------------------------------
# MAIN LEARNING FUNCTION
# --------------------------------------------------

def learn_from_interaction(user_input, response, intent):

    data = load_data()
    now = datetime.datetime.now()

    # Last seen
    data["last_seen"] = now.strftime("%Y-%m-%d %H:%M")

    # Safe dictionaries
    data.setdefault("topic_frequency", {})
    data.setdefault("intent_weights", {})
    data.setdefault("behavior_stats", {
        "short_queries": 0,
        "medium_queries": 0,
        "long_queries": 0
    })

    # Topic tracking
    data["topic_frequency"][intent] = data["topic_frequency"].get(intent, 0) + 1

    # Intent weighting
    data["intent_weights"][intent] = data["intent_weights"].get(intent, 0) + 2

    # Behavior tracking
    length_type = analyze_query_length(user_input)
    data["behavior_stats"][f"{length_type}_queries"] += 1

    # Interaction history
    interaction = {
        "time": now.strftime("%Y-%m-%d %H:%M"),
        "intent": intent,
        "input": user_input[:200],
        "response": response[:200],
        "length_type": length_type
    }

    data["interaction_history"].append(interaction)

    if len(data["interaction_history"]) > 300:
        data["interaction_history"] = data["interaction_history"][-300:]

    # Intent sequence
    if len(data["interaction_history"]) >= 2:
        prev = data["interaction_history"][-2]["intent"]
        data["intent_sequences"].append((prev, intent))

    # Facts
    fact = extract_fact(user_input)
    if fact and fact not in data["learned_facts"]:
        data["learned_facts"].append(fact)

    # Vector memory
    store_memory(f"User: {user_input}", {"intent": intent})

    save_data(data)


# --------------------------------------------------
# USER INSIGHTS
# --------------------------------------------------

def get_user_insights():

    data = load_data()

    if not data["interaction_history"]:
        return "Still learning about you..."

    top_intents = Counter(data["topic_frequency"]).most_common(5)

    result = "🧠 USER PROFILE\n\n"

    for i, (intent, count) in enumerate(top_intents, 1):
        result += f"{i}. {intent} → {count} times\n"

    stats = data["behavior_stats"]

    result += "\n📊 Behavior:\n"
    result += f"Short: {stats['short_queries']} | "
    result += f"Medium: {stats['medium_queries']} | "
    result += f"Long: {stats['long_queries']}\n"

    result += f"\n🕒 Last seen: {data['last_seen']}\n"

    return result


# --------------------------------------------------
# NEXT INTENT PREDICTION
# --------------------------------------------------

def predict_next_intent():

    data = load_data()

    if not data["intent_sequences"]:
        return None

    sequences = Counter(data["intent_sequences"])
    return sequences.most_common(1)[0][0][1]


# --------------------------------------------------
# PERSONALIZED GREETING
# --------------------------------------------------

def get_personalized_greeting():

    data = load_data()

    if not data["topic_frequency"]:
        return "Hey! I'm still getting to know you 😄"

    favorite = max(data["topic_frequency"], key=data["topic_frequency"].get)

    return f"Welcome back! Want to continue with {favorite}?"


# --------------------------------------------------
# CONTEXT BUILDER
# --------------------------------------------------

def build_context(user_input):

    memories = search_memory(user_input)

    context = "\n".join([m["text"] for m in memories[:3]])

    return f"""
Relevant memory:
{context}

User:
{user_input}
"""


# --------------------------------------------------
# PREFERENCE LEARNING
# --------------------------------------------------

def learn_preference(key, value):

    data = load_data()
    data["user_profile"]["preferences"][key] = value
    save_data(data)

    return f"Got it. I'll remember {key} = {value}"


# --------------------------------------------------
# SELF REFLECTION
# --------------------------------------------------

def self_reflection():

    data = load_data()

    if len(data["interaction_history"]) < 30:
        return "Not enough data yet."

    top = Counter(data["topic_frequency"]).most_common(3)

    report = "🤖 SELF REPORT\n\nTop skills:\n"

    for t in top:
        report += f"- {t[0]} ({t[1]})\n"

    report += "\nSystem adapting successfully."

    return report