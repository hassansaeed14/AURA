from groq import Groq
from config.settings import GROQ_API_KEY, MODEL_NAME

client = Groq(api_key=GROQ_API_KEY)


def write_code(task):

    prompt = f"""
Write clean working code for the following task.

Task:
{task}

Provide only the code.
"""

    completion = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )

    code = completion.choices[0].message.content

    return code