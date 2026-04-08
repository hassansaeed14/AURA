from groq import Groq
from config.settings import GROQ_API_KEY, MODEL_NAME, AURA_PERSONALITY

client = Groq(api_key=GROQ_API_KEY)

def reason(problem, context=None):
    print(f"\nAURA Reasoning Agent: {problem[:50]}")

    system = (
        f"{AURA_PERSONALITY} "
        "You are AURA Reasoning Agent — you think through complex problems step by step. "
        "Format:\n"
        "PROBLEM ANALYSIS\n\n"
        "UNDERSTANDING:\n[What exactly is being asked]\n\n"
        "REASONING STEPS:\n"
        "Step 1: [First logical step]\n"
        "Step 2: [Second logical step]\n"
        "Step 3: [Third logical step]\n\n"
        "CONCLUSION:\n[Final reasoned answer]\n\n"
        "CONFIDENCE: [High/Medium/Low]\n"
        "No markdown symbols."
    )

    messages = [{"role": "system", "content": system}]
    if context:
        messages.append({"role": "user", "content": f"Context: {context}"})
    messages.append({"role": "user", "content": f"Reason through this: {problem}"})

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        max_tokens=1000
    )
    return response.choices[0].message.content

def analyze_pros_cons(topic):
    print(f"\nAURA Reasoning Agent: pros/cons of {topic}")

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are AURA Reasoning Agent. "
                    "Analyze pros and cons objectively. "
                    "Format:\n"
                    "PROS AND CONS ANALYSIS: [topic]\n\n"
                    "PROS:\n"
                    "1. [Pro]\n"
                    "2. [Pro]\n"
                    "3. [Pro]\n\n"
                    "CONS:\n"
                    "1. [Con]\n"
                    "2. [Con]\n"
                    "3. [Con]\n\n"
                    "VERDICT:\n[Balanced conclusion]\n\n"
                    "RECOMMENDATION:\n[What you suggest]"
                )
            },
            {"role": "user", "content": f"Analyze pros and cons of: {topic}"}
        ],
        max_tokens=800
    )
    return response.choices[0].message.content

def compare(item1, item2):
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are AURA Reasoning Agent. "
                    "Compare two items objectively. "
                    "Format:\n"
                    "COMPARISON: [item1] vs [item2]\n\n"
                    "ITEM 1: [name]\n"
                    "Strengths: [strengths]\n"
                    "Weaknesses: [weaknesses]\n\n"
                    "ITEM 2: [name]\n"
                    "Strengths: [strengths]\n"
                    "Weaknesses: [weaknesses]\n\n"
                    "KEY DIFFERENCES:\n"
                    "1. [Difference]\n"
                    "2. [Difference]\n\n"
                    "WINNER: [Which is better and why]\n\n"
                    "USE CASE:\n[When to use each one]"
                )
            },
            {"role": "user", "content": f"Compare {item1} vs {item2}"}
        ],
        max_tokens=800
    )
    return response.choices[0].message.content