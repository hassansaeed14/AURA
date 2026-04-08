import re
from groq import Groq
from config.settings import GROQ_API_KEY, MODEL_NAME
from memory.vector_memory import store_memory


client = Groq(api_key=GROQ_API_KEY)

LANGUAGES = {
    "urdu": "Urdu",
    "english": "English",
    "arabic": "Arabic",
    "french": "French",
    "spanish": "Spanish",
    "german": "German",
    "chinese": "Chinese",
    "hindi": "Hindi",
    "punjabi": "Punjabi",
    "turkish": "Turkish",
    "russian": "Russian",
    "japanese": "Japanese",
    "korean": "Korean",
    "italian": "Italian",
    "portuguese": "Portuguese"
}


def clean(text):
    if not text:
        return "Translation failed."

    text = str(text)
    text = re.sub(r"\*{1,3}(.*?)\*{1,3}", r"\1", text)
    text = re.sub(r"#{1,6}\s*", "", text)
    text = re.sub(r"`{3}[\w]*\n?", "", text)
    text = re.sub(r"`(.+?)`", r"\1", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def normalize_language(lang):
    if not lang:
        return "English"

    lang = lang.lower().strip()
    return LANGUAGES.get(lang, lang.capitalize())


def extract_text_only(command):
    command = command.strip()

    # remove common prefixes
    patterns = [
        r"translate (this )?to \w+:?",
        r"translate (this )?",
        r"translation of",
    ]

    cleaned = command.lower()
    for p in patterns:
        cleaned = re.sub(p, "", cleaned)

    return cleaned.strip()


def translate(text, target_language="urdu", source_language="auto"):
    try:
        target = normalize_language(target_language)

        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are AURA Translation Agent. "
                        "Translate text accurately and naturally.\n\n"
                        "Structure:\n"
                        "ORIGINAL TEXT\n"
                        "TRANSLATION\n"
                        "NOTES (optional)\n\n"
                        "Do not use markdown symbols like *, #, or backticks."
                    )
                },
                {
                    "role": "user",
                    "content": f"Translate this to {target}: {text}"
                }
            ],
            max_tokens=1000,
            temperature=0.2
        )

        result = response.choices[0].message.content if response.choices else ""
        cleaned = clean(result)

        store_memory(
            f"Translated text to {target}: {text[:50]}",
            {
                "type": "translation",
                "target": target
            }
        )

        return cleaned

    except Exception as e:
        return f"Translation error: {str(e)}"


def detect_and_translate(text):
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are AURA Translation Agent.\n\n"
                        "1. Detect the language\n"
                        "2. Translate:\n"
                        "- If English → Urdu\n"
                        "- If not English → English\n\n"
                        "Structure:\n"
                        "DETECTED LANGUAGE\n"
                        "ORIGINAL\n"
                        "TRANSLATION\n\n"
                        "Do not use markdown symbols."
                    )
                },
                {
                    "role": "user",
                    "content": f"Detect and translate: {text}"
                }
            ],
            max_tokens=500,
            temperature=0.2
        )

        result = response.choices[0].message.content if response.choices else ""
        cleaned = clean(result)

        store_memory(
            f"Auto translation: {text[:50]}",
            {
                "type": "translation_auto"
            }
        )

        return cleaned

    except Exception as e:
        return f"Detect+Translate error: {str(e)}"