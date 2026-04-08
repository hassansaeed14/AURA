from groq import Groq
from config.settings import GROQ_API_KEY, MODEL_NAME

client = Groq(api_key=GROQ_API_KEY)

def get_quote(category="motivation"):
    print(f"\nAURA Quote Agent: {category}")

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are AURA Quote Agent. "
                    "Share inspiring and meaningful quotes. "
                    "Format:\n"
                    "QUOTE:\n"
                    "[The quote]\n\n"
                    "AUTHOR: [Who said it]\n\n"
                    "MEANING:\n"
                    "[What this quote means and how to apply it]\n\n"
                    "REFLECTION:\n"
                    "[A thought to reflect on]"
                )
            },
            {"role": "user", "content": f"Give me a {category} quote"}
        ],
        max_tokens=300
    )
    return response.choices[0].message.content

def get_daily_quote():
    return get_quote("daily inspiration")

def get_islamic_quote():
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are AURA Quote Agent. "
                    "Share an Islamic quote or hadith. "
                    "Format:\n"
                    "ISLAMIC QUOTE\n\n"
                    "ARABIC:\n[Arabic text if applicable]\n\n"
                    "TRANSLATION:\n[English translation]\n\n"
                    "SOURCE: [Quran/Hadith reference]\n\n"
                    "LESSON:\n[What we can learn from this]"
                )
            },
            {"role": "user", "content": "Share an Islamic quote or hadith"}
        ],
        max_tokens=400
    )
    return response.choices[0].message.content