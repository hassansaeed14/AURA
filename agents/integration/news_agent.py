import re
import requests
from groq import Groq
from config.settings import GROQ_API_KEY, MODEL_NAME
from memory.vector_memory import store_memory


client = Groq(api_key=GROQ_API_KEY)


def clean(text):
    if not text:
        return "No news available right now."

    text = str(text)
    text = re.sub(r"\*{1,3}(.*?)\*{1,3}", r"\1", text)
    text = re.sub(r"#{1,6}\s*", "", text)
    text = re.sub(r"`{3}[\w]*\n?", "", text)
    text = re.sub(r"`(.+?)`", r"\1", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def get_news(topic="general"):
    try:
        # ⚠️ NOTE: Replace with real API key later
        url = "https://gnews.io/api/v4/search"

        response = requests.get(
            url,
            params={
                "q": topic,
                "lang": "en",
                "max": 5,
                "apikey": "free"  # <-- replace with real key later
            },
            timeout=10
        )

        response.raise_for_status()
        data = response.json()

        articles = data.get("articles", [])

        if not articles:
            return get_news_from_ai(topic)

        result = f"LATEST NEWS: {topic.upper()}\n\n"

        for i, article in enumerate(articles[:5], 1):
            title = article.get("title", "No title")
            source = article.get("source", {}).get("name", "Unknown")
            desc = article.get("description", "")

            result += f"{i}. {title}\n"
            result += f"   Source: {source}\n"
            if desc:
                result += f"   {desc}\n"
            result += "\n"

        store_memory(
            f"News searched: {topic}",
            {
                "type": "news",
                "topic": topic
            }
        )

        return result.strip()

    except Exception:
        return get_news_from_ai(topic)


def get_news_from_ai(topic):
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are AURA News Agent. "
                        "Provide a realistic recent-style news summary in plain text.\n\n"
                        "Structure:\n"
                        "LATEST NEWS\n"
                        "1. Title\nDescription\n"
                        "2. Title\nDescription\n"
                        "3. Title\nDescription\n\n"
                        "Keep it informative. No markdown symbols."
                    )
                },
                {
                    "role": "user",
                    "content": f"Give me latest news about: {topic}"
                }
            ],
            max_tokens=900,
            temperature=0.4
        )

        result = response.choices[0].message.content if response.choices else ""
        cleaned = clean(result)

        store_memory(
            f"AI news fallback: {topic}",
            {
                "type": "news_fallback",
                "topic": topic
            }
        )

        return cleaned

    except Exception as e:
        return f"News Agent error: {str(e)}"


def get_pakistan_news():
    return get_news("Pakistan latest news")


def get_tech_news():
    return get_news("technology AI")


def get_sports_news():
    return get_news("sports")