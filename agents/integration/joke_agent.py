from groq import Groq
from config.settings import GROQ_API_KEY, MODEL_NAME

client = Groq(api_key=GROQ_API_KEY)

def get_joke(category="general"):
    print(f"\nAURA Joke Agent: {category}")

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are AURA Joke Agent, a friendly comedian. "
                    "Tell funny, clean and appropriate jokes. "
                    "Format:\n"
                    "JOKE:\n"
                    "[Setup]\n\n"
                    "PUNCHLINE:\n"
                    "[Punchline]\n\n"
                    "Keep it clean and family friendly."
                )
            },
            {"role": "user", "content": f"Tell me a {category} joke"}
        ],
        max_tokens=200
    )
    return response.choices[0].message.content

def get_programming_joke():
    return get_joke("programming")

def get_urdu_joke():
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": (
                    "آپ AURA Joke Agent ہیں۔ "
                    "اردو میں مزاحیہ اور صاف لطیفہ سنائیں۔ "
                    "فارمیٹ:\n"
                    "لطیفہ:\n"
                    "[لطیفہ]\n\n"
                    "خلاصہ:\n"
                    "[مضحکہ خیز نقطہ]"
                )
            },
            {"role": "user", "content": "اردو میں ایک مزاحیہ لطیفہ سنائیں"}
        ],
        max_tokens=200
    )
    return response.choices[0].message.content