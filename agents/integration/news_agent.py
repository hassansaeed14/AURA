import requests
from groq import Groq
from config.settings import GROQ_API_KEY, MODEL_NAME

client = Groq(api_key=GROQ_API_KEY)

def get_news(topic="general"):
    print(f"\nAURA News Agent: {topic}")

    try:
        # Using GNews free API
        url = f"https://gnews.io/api/v4/search?q={topic}&lang=en&max=5&apikey=free"
        response = requests.get(url, timeout=10)
        data = response.json()

        if 'articles' not in data or len(data['articles']) == 0:
            return get_news_from_ai(topic)

        result = f"Latest News on: {topic}\n\n"
        for i, article in enumerate(data['articles'][:5], 1):
            result += f"{i}. {article['title']}\n"
            result += f"   Source: {article['source']['name']}\n"
            result += f"   {article['description']}\n\n"

        return result

    except:
        return get_news_from_ai(topic)

def get_news_from_ai(topic):
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are AURA News Agent. "
                    "Provide latest news summary on the given topic. "
                    "Format as numbered news items with title and brief description. "
                    "Be informative and factual. No markdown symbols."
                )
            },
            {
                "role": "user",
                "content": f"Give me latest news about: {topic}"
            }
        ],
        max_tokens=1000
    )
    return response.choices[0].message.content

def get_pakistan_news():
    return get_news("Pakistan latest news")

def get_tech_news():
    return get_news("technology AI")

def get_sports_news():
    return get_news("sports")