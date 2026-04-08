from groq import Groq
from config.settings import GROQ_API_KEY, MODEL_NAME

client = Groq(api_key=GROQ_API_KEY)

def check_grammar(text):
    print(f"\nAURA Grammar Agent: checking text")

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are AURA Grammar Agent, an expert English teacher. "
                    "Check grammar, spelling and style. "
                    "Format:\n"
                    "GRAMMAR CHECK REPORT\n\n"
                    "ORIGINAL TEXT:\n[original text]\n\n"
                    "CORRECTED TEXT:\n[corrected version]\n\n"
                    "ERRORS FOUND:\n"
                    "1. Error: [what was wrong]\n"
                    "   Correction: [what it should be]\n"
                    "   Rule: [grammar rule]\n\n"
                    "STYLE SUGGESTIONS:\n"
                    "1. [Suggestion to improve writing]\n"
                    "2. [Suggestion]\n\n"
                    "OVERALL SCORE: [X/10]\n"
                    "FEEDBACK: [General feedback on writing quality]"
                )
            },
            {"role": "user", "content": f"Check grammar of: {text}"}
        ],
        max_tokens=1000
    )
    return response.choices[0].message.content

def improve_writing(text, style="professional"):
    print(f"\nAURA Grammar Agent: improving writing")

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": (
                    f"You are AURA Grammar Agent. "
                    f"Improve the writing to be more {style}. "
                    f"Format:\n"
                    f"WRITING IMPROVEMENT\n\n"
                    f"ORIGINAL:\n[original text]\n\n"
                    f"IMPROVED ({style}):\n[improved version]\n\n"
                    f"CHANGES MADE:\n"
                    f"1. [Change and why]\n"
                    f"2. [Change and why]\n"
                    f"3. [Change and why]\n\n"
                    f"TIPS FOR BETTER WRITING:\n"
                    f"1. [Tip]\n"
                    f"2. [Tip]"
                )
            },
            {"role": "user", "content": f"Improve this text in {style} style: {text}"}
        ],
        max_tokens=1000
    )
    return response.choices[0].message.content

def paraphrase(text):
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are AURA Grammar Agent. "
                    "Paraphrase the text in 3 different ways. "
                    "Format:\n"
                    "PARAPHRASE OPTIONS\n\n"
                    "ORIGINAL:\n[original]\n\n"
                    "VERSION 1 (Formal):\n[formal version]\n\n"
                    "VERSION 2 (Simple):\n[simple version]\n\n"
                    "VERSION 3 (Creative):\n[creative version]"
                )
            },
            {"role": "user", "content": f"Paraphrase: {text}"}
        ],
        max_tokens=800
    )
    return response.choices[0].message.content