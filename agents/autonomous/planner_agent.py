from groq import Groq
from config.settings import GROQ_API_KEY, MODEL_NAME

client = Groq(api_key=GROQ_API_KEY)


def create_plan(user_request):

    prompt = f"""
You are an AI task planner.

Break the user request into clear step-by-step tasks.

User request:
{user_request}

Return numbered steps only.
"""

    completion = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )

    plan = completion.choices[0].message.content

    return plan