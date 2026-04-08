from groq import Groq
from config.settings import GROQ_API_KEY, MODEL_NAME

client = Groq(api_key=GROQ_API_KEY)


# -------------------------------
# LANGUAGE DETECTION
# -------------------------------

def detect_language(text):

    prompt = f"""
Detect the language of this text.

Return only one word.

Text:
{text}
"""

    try:

        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )

        language = completion.choices[0].message.content.strip().lower()

        return language

    except:
        return "english"


# -------------------------------
# RESPONSE TRANSLATION
# -------------------------------

def respond_in_language(response, language):

    if language == "english":
        return response

    prompt = f"""
Translate the following response into {language}.

Response:
{response}
"""

    try:

        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )

        translated = completion.choices[0].message.content

        return translated

    except:
        return response