from groq import Groq
from config.settings import GROQ_API_KEY, MODEL_NAME

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

def translate(text, target_language="urdu", source_language="auto"):
    print(f"\nAURA Translation Agent: {text[:50]}... to {target_language}")

    target = LANGUAGES.get(target_language.lower(), target_language)

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": (
                    f"You are AURA Translation Agent, an expert translator. "
                    f"Translate the given text to {target}. "
                    f"Format:\n"
                    f"ORIGINAL TEXT:\n[original text]\n\n"
                    f"TRANSLATION ({target}):\n[translated text]\n\n"
                    f"NOTES:\n[any translation notes or cultural context]\n"
                    f"Be accurate and natural in translation."
                )
            },
            {
                "role": "user",
                "content": f"Translate this to {target}: {text}"
            }
        ],
        max_tokens=1000
    )
    return response.choices[0].message.content

def detect_and_translate(text):
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are AURA Translation Agent. "
                    "First detect the language of the text, "
                    "then translate it to English if not English, "
                    "or to Urdu if it is English. "
                    "Format:\n"
                    "DETECTED LANGUAGE: [language]\n"
                    "ORIGINAL: [original text]\n"
                    "TRANSLATION: [translated text]"
                )
            },
            {
                "role": "user",
                "content": f"Detect and translate: {text}"
            }
        ],
        max_tokens=500
    )
    return response.choices[0].message.content