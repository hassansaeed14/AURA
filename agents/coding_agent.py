from groq import Groq
from config.settings import GROQ_API_KEY, MODEL_NAME

client = Groq(api_key=GROQ_API_KEY)

def code_help(request):
    print(f"\nAURA Coding Agent activated for: {request}")
    
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": """You are AURA's Coding Agent.
                Help with programming questions, write code, and debug errors.
                Always explain what the code does.
                Keep explanations simple, clear, Brief and Useful.
                Never use symbols like *, #, ` in your response.
                Write in plain text only."""
            },
            {
                "role": "user",
                "content": f"Help me with this coding request: {request}"
            }
        ]
    )
    
    return response.choices[0].message.content