import re
from groq import Groq
from config.settings import GROQ_API_KEY, MODEL_NAME, AURA_PERSONALITY


client = Groq(api_key=GROQ_API_KEY)

conversation_history = []
MAX_HISTORY_MESSAGES = 20
RECENT_CONTEXT_MESSAGES = 10
DEFAULT_MAX_TOKENS = 2000
DEFAULT_TEMPERATURE = 0.4


def detect_language(text):
    urdu_chars = set("ابتثجحخدذرزسشصضطظعغفقکگلمنوہیئاآ")
    count = sum(1 for char in str(text) if char in urdu_chars)
    return "urdu" if count > 2 else "english"


def clean_response(text):
    if not text:
        return "I couldn't generate a response right now."

    text = str(text)
    text = re.sub(r"\*{1,3}(.*?)\*{1,3}", r"\1", text)
    text = re.sub(r"#{1,6}\s*", "", text)
    text = re.sub(r"`{3}[\w]*\n?", "", text)
    text = re.sub(r"`(.+?)`", r"\1", text)
    text = re.sub(r"_{2,}", "", text)
    text = re.sub(r">+\s*", "", text)
    text = re.sub(r"\[(.+?)\]\((.+?)\)", r"\1", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\s+\n", "\n", text)
    return text.strip()


def add_to_history(role, content):
    if not content:
        return

    item = {
        "role": role,
        "content": str(content).strip()
    }

    if conversation_history and conversation_history[-1] == item:
        return

    conversation_history.append(item)

    if len(conversation_history) > MAX_HISTORY_MESSAGES:
        del conversation_history[:-MAX_HISTORY_MESSAGES]


def build_system_prompt(language, system_override=None):
    if system_override:
        return system_override

    if language == "urdu":
        return (
            f"{AURA_PERSONALITY} "
            "آپ AURA ہیں، ایک ذہین، دوستانہ اور قدرتی انداز میں بات کرنے والی AI اسسٹنٹ۔ "
            "اگر صارف اردو میں بات کرے تو اردو میں جواب دیں۔ "
            "سادہ، صاف اور قدرتی انداز میں جواب دیں۔ "
            "سوال آسان ہو تو مختصر جواب دیں، اور تفصیلی سوال ہو تو مکمل جواب دیں۔ "
            "گفتگو کا سیاق و سباق برقرار رکھیں۔ "
            "اپنے بنانے والے کا ذکر صرف اسی وقت کریں جب صارف براہ راست پوچھے۔ "
            "مارک ڈاؤن علامات جیسے *، #، یا ``` استعمال نہ کریں۔"
        )

    return (
        f"{AURA_PERSONALITY} "
        "You are AURA, a highly intelligent, warm, and conversational AI assistant. "
        "Match response length to the user's request. "
        "Simple question means a short clear answer. "
        "Complex request means a detailed structured answer. "
        "Maintain conversation context and continuity. "
        "Only mention your creator if the user directly asks who made or created you. "
        "Do not use markdown symbols like *, **, #, ##, or backticks in normal replies. "
        "Write in plain natural text. "
        "Avoid repetition. "
        "Be direct, helpful, and non-robotic. "
        "If the user asks what something is, give a short clear answer unless they ask for detail."
    )


def build_messages(user_input, system_prompt):
    recent_history = conversation_history[-RECENT_CONTEXT_MESSAGES:]
    return [{"role": "system", "content": system_prompt}] + recent_history + [
        {"role": "user", "content": str(user_input).strip()}
    ]


def get_ai_response(user_input, system_override=None, max_tokens=DEFAULT_MAX_TOKENS, temperature=DEFAULT_TEMPERATURE):
    language = detect_language(user_input)
    system_prompt = build_system_prompt(language, system_override=system_override)
    messages = build_messages(user_input, system_prompt)

    add_to_history("user", user_input)

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature
        )

        result = response.choices[0].message.content if response.choices else ""
        cleaned = clean_response(result)

        if not cleaned:
            cleaned = "I couldn't generate a useful response right now."

    except Exception as e:
        cleaned = f"AI response error: {str(e)}"

    add_to_history("assistant", cleaned)
    return cleaned


def generate_response(user_input, system_override=None, max_tokens=DEFAULT_MAX_TOKENS, temperature=DEFAULT_TEMPERATURE):
    return get_ai_response(
        user_input=user_input,
        system_override=system_override,
        max_tokens=max_tokens,
        temperature=temperature
    )


def clear_history():
    conversation_history.clear()


def get_conversation_history():
    return conversation_history[-RECENT_CONTEXT_MESSAGES:]