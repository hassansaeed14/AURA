import requests
from groq import Groq
from config.settings import GROQ_API_KEY, MODEL_NAME

client = Groq(api_key=GROQ_API_KEY)

PROGRAMMING_TERMS = [
    "python", "java", "javascript", "html", "css", "sql",
    "api", "algorithm", "variable", "function", "class",
    "object", "array", "loop", "recursion", "database",
    "framework", "library", "compiler", "debugging", "git",
    "react", "node", "django", "flask", "machine learning",
    "ai", "neural network", "deep learning", "data science"
]

def define_programming_term(term):
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are AURA Dictionary Agent specializing in programming and technology. "
                    "Define programming terms clearly. "
                    "Format:\n"
                    "TERM: [term]\n"
                    "TYPE: [Programming Language / Framework / Concept]\n\n"
                    "DEFINITION:\n[Clear definition]\n\n"
                    "KEY FEATURES:\n"
                    "1. [Feature]\n"
                    "2. [Feature]\n"
                    "3. [Feature]\n\n"
                    "COMMON USE CASES:\n"
                    "[Where it is used]\n\n"
                    "EXAMPLE:\n[Simple code or usage example]\n\n"
                    "No markdown symbols."
                )
            },
            {"role": "user", "content": f"Define this programming term: {term}"}
        ],
        max_tokens=600
    )
    return response.choices[0].message.content

def define_word(word):
    print(f"\nAURA Dictionary Agent: {word}")

    # For programming terms use AI directly
    if word.lower() in PROGRAMMING_TERMS:
        return define_programming_term(word)

    try:
        url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
        response = requests.get(url, timeout=10)
        data = response.json()

        if isinstance(data, list) and len(data) > 0:
            entry = data[0]
            word_text = entry.get('word', word)
            phonetic = entry.get('phonetic', '')

            result = f"Dictionary: {word_text.upper()}\n"
            if phonetic:
                result += f"Pronunciation: {phonetic}\n\n"

            meanings = entry.get('meanings', [])
            for i, meaning in enumerate(meanings[:3], 1):
                part = meaning.get('partOfSpeech', '')
                result += f"{i}. {part.upper()}\n"
                definitions = meaning.get('definitions', [])
                for j, defn in enumerate(definitions[:2], 1):
                    result += f"   Definition: {defn.get('definition', '')}\n"
                    if defn.get('example'):
                        result += f"   Example: {defn.get('example')}\n"
                result += "\n"

            synonyms = meanings[0].get('synonyms', [])[:5] if meanings else []
            if synonyms:
                result += f"Synonyms: {', '.join(synonyms)}\n"

            return result

    except:
        pass

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are AURA Dictionary Agent. "
                    "Define words clearly with pronunciation, meaning, examples and synonyms. "
                    "Format:\n"
                    "WORD: [word]\n"
                    "PRONUNCIATION: [how to say it]\n"
                    "PART OF SPEECH: [noun/verb/etc]\n"
                    "DEFINITION: [clear definition]\n"
                    "EXAMPLE: [example sentence]\n"
                    "SYNONYMS: [similar words]\n"
                    "ANTONYMS: [opposite words]\n"
                    "No markdown symbols."
                )
            },
            {"role": "user", "content": f"Define the word: {word}"}
        ],
        max_tokens=500
    )
    return response.choices[0].message.content

def get_synonyms(word):
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": "You are AURA Dictionary Agent. Give synonyms and antonyms. No markdown."
            },
            {"role": "user", "content": f"Give synonyms and antonyms for: {word}"}
        ],
        max_tokens=300
    )
    return response.choices[0].message.content