from groq import Groq
from config.settings import GROQ_API_KEY, MODEL_NAME, APP_NAME
import re

client = Groq(api_key=GROQ_API_KEY)

def detect_language(text):
    urdu_chars = set('ابتثجحخدذرزسشصضطظعغفقکگلمنوہیئاآ')
    count = sum(1 for char in text if char in urdu_chars)
    return "urdu" if count > 2 else "english"

def clean_response(text):
    text = re.sub(r'\*+', '', text)
    text = re.sub(r'#+', '', text)
    text = re.sub(r'`+', '', text)
    text = re.sub(r'\-\-+', '', text)
    text = re.sub(r'\[|\]|\(|\)', '', text)
    text = re.sub(r'>\s*', '', text)
    text = re.sub(r'\|', '', text)
    text = re.sub(r'_{2,}', '', text)
    text = re.sub(r'\n+', '\n', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def generate_response(user_input):
    language = detect_language(user_input)

    if language == "urdu":
        system_prompt = """آپ AURA ہیں، ایک ذہین اور مددگار AI اسسٹنٹ۔
        ہمیشہ اردو میں جواب دیں۔
        طلباء کے لیے تفصیلی اور واضح جوابات دیں۔
        مثالوں کے ساتھ سمجھائیں۔
        کوئی بھی خاص علامات جیسے * # یا backticks استعمال نہ کریں۔
        سادہ متن میں لکھیں۔"""
    else:
        system_prompt = f"""You are {APP_NAME}, a highly intelligent personal AI assistant.
        You are talking to a university student.
        Give detailed, educational and helpful responses.
        Use simple language but cover the topic thoroughly.
        Give examples when explaining concepts.
        IMPORTANT: Never use any markdown symbols like *, **, #, ##, `, or special characters.
        Never use bullet points with dashes or asterisks.
        Write in plain numbered points like: 1. 2. 3.
        Write in clean plain text only.
        Be like a knowledgeable friend who explains things clearly."""

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ]
    )

    result = response.choices[0].message.content
    return clean_response(result)