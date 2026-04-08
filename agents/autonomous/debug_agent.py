from groq import Groq
from config.settings import GROQ_API_KEY, MODEL_NAME

client = Groq(api_key=GROQ_API_KEY)


def fix_code(code):

    prompt = f"""
Fix errors in this code and return the corrected version.

Code:
{code}
"""

    completion = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )

    fixed = completion.choices[0].message.content

    return fixed