import re
from typing import List, Dict, Optional

from brain.provider_hub import generate_with_best_provider, summarize_provider_statuses
from config.settings import AURA_PERSONALITY, DEFAULT_REASONING_PROVIDER, MODEL_NAME

conversation_history: List[Dict[str, str]] = []

MAX_HISTORY_MESSAGES = 20
RECENT_CONTEXT_MESSAGES = 10
DEFAULT_MAX_TOKENS = 2000
DEFAULT_TEMPERATURE = 0.4

FALLBACK_USER_MESSAGE = "I ran into a problem while generating a response. Please try again."


def detect_language(text: str) -> str:
    urdu_chars = set("ابتثجحخدذرزسشصضطظعغفقکگلمنوہیئاآ")
    count = sum(1 for char in str(text) if char in urdu_chars)
    return "urdu" if count > 2 else "english"


def is_meaningful_text(text: Optional[str]) -> bool:
    if text is None:
        return False

    stripped = str(text).strip()
    if not stripped:
        return False

    cleaned = stripped.strip(" \n\t.,!?;:-_")
    return bool(cleaned)


def clean_response(text: Optional[str]) -> str:
    if not is_meaningful_text(text):
        return ""

    text = str(text)

    # Keep plain text friendly, but avoid over-destroying useful content
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


def add_to_history(role: str, content: str) -> None:
    if not is_meaningful_text(content):
        return

    item = {
        "role": str(role).strip(),
        "content": str(content).strip(),
    }

    if conversation_history and conversation_history[-1] == item:
        return

    conversation_history.append(item)

    if len(conversation_history) > MAX_HISTORY_MESSAGES:
        del conversation_history[:-MAX_HISTORY_MESSAGES]


def build_system_prompt(language: str, system_override: Optional[str] = None) -> str:
    if is_meaningful_text(system_override):
        return str(system_override).strip()

    if language == "urdu":
        return (
            f"{AURA_PERSONALITY} "
            "آپ AURA ہیں، ایک ذہین، دوستانہ اور قدرتی انداز میں بات کرنے والی AI اسسٹنٹ۔ "
            "اگر صارف اردو میں بات کرے تو اردو میں جواب دیں۔ "
            "سادہ، صاف اور قدرتی انداز میں جواب دیں۔ "
            "سوال آسان ہو تو مختصر جواب دیں، اور تفصیلی سوال ہو تو مکمل جواب دیں۔ "
            "گفتگو کا سیاق و سباق برقرار رکھیں۔ "
            "اپنے بنانے والے کا ذکر صرف اسی وقت کریں جب صارف براہ راست پوچھے۔ "
            "عام جواب میں غیر ضروری مارک ڈاؤن علامات استعمال نہ کریں۔"
        )

    return (
        f"{AURA_PERSONALITY} "
        "You are AURA, a highly intelligent, warm, and conversational AI assistant. "
        "You are a modular AI operating system assistant, not just a chat box. "
        "Match response length to the user's request. "
        "Simple question means a short clear answer. "
        "Complex request means a detailed structured answer. "
        "Maintain conversation context and continuity. "
        "Only mention your creator if the user directly asks who made or created you. "
        "Avoid unnecessary markdown symbols in normal replies. "
        "Write in plain natural text. "
        "Avoid repetition. "
        "Be direct, helpful, and natural. "
        "If the user asks what something is, give a short clear answer unless they ask for detail. "
        "Do not fake capabilities or claim a system action succeeded unless it actually ran."
    )


def build_messages(user_input: str, system_prompt: str) -> List[Dict[str, str]]:
    recent_history = conversation_history[-RECENT_CONTEXT_MESSAGES:]
    return [{"role": "system", "content": system_prompt}] + recent_history + [
        {"role": "user", "content": str(user_input).strip()}
    ]


def extract_response_content(response) -> str:
    try:
        if not response or not getattr(response, "choices", None):
            return ""

        first_choice = response.choices[0]
        if not first_choice:
            return ""

        message = getattr(first_choice, "message", None)
        if not message:
            return ""

        content = getattr(message, "content", "")
        return str(content).strip() if content is not None else ""
    except Exception:
        return ""


def get_ai_response(
    user_input: str,
    system_override: Optional[str] = None,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    temperature: float = DEFAULT_TEMPERATURE
) -> str:
    if not is_meaningful_text(user_input):
        return "Please say something so I can respond."

    language = detect_language(user_input)
    system_prompt = build_system_prompt(language, system_override=system_override)
    messages = build_messages(user_input, system_prompt)

    try:
        provider_response = generate_with_best_provider(
            messages,
            preferred=DEFAULT_REASONING_PROVIDER,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        raw_result = str(provider_response.get("text", "")).strip()
        cleaned = clean_response(raw_result)

        if not is_meaningful_text(cleaned):
            return "I couldn't generate a useful response right now."

        # Commit to history only after a valid response exists
        add_to_history("user", user_input)
        add_to_history("assistant", cleaned)

        return cleaned

    except Exception:
        return FALLBACK_USER_MESSAGE


def generate_response(
    user_input: str,
    system_override: Optional[str] = None,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    temperature: float = DEFAULT_TEMPERATURE
) -> str:
    return get_ai_response(
        user_input=user_input,
        system_override=system_override,
        max_tokens=max_tokens,
        temperature=temperature
    )


def get_provider_summary() -> Dict[str, object]:
    return summarize_provider_statuses()


def clear_history() -> None:
    conversation_history.clear()


def get_conversation_history() -> List[Dict[str, str]]:
    return conversation_history[-RECENT_CONTEXT_MESSAGES:]
