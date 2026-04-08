import requests
from bs4 import BeautifulSoup
from groq import Groq
from config.settings import GROQ_API_KEY, MODEL_NAME

client = Groq(api_key=GROQ_API_KEY)

def web_search(query):
    print(f"\nAURA Web Search Agent: {query}")

    try:
        # Use DuckDuckGo instant answer API
        url = f"https://api.duckduckgo.com/?q={query}&format=json&no_html=1"
        response = requests.get(url, timeout=10)
        data = response.json()

        result = f"Web Search Results for: {query}\n\n"

        if data.get('Abstract'):
            result += f"Summary:\n{data['Abstract']}\n\n"

        if data.get('RelatedTopics'):
            result += "Related Information:\n"
            for i, topic in enumerate(data['RelatedTopics'][:5], 1):
                if isinstance(topic, dict) and topic.get('Text'):
                    result += f"{i}. {topic['Text']}\n\n"

        if len(result) < 100:
            return search_with_ai(query)

        return result

    except:
        return search_with_ai(query)

def search_with_ai(query):
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are AURA Web Search Agent. "
                    "Provide comprehensive search results for the query. "
                    "Format:\n"
                    "SEARCH RESULTS FOR: [query]\n\n"
                    "TOP RESULT:\n[Most relevant information]\n\n"
                    "KEY FACTS:\n"
                    "1. [Fact]\n"
                    "2. [Fact]\n"
                    "3. [Fact]\n\n"
                    "ADDITIONAL INFO:\n[More details]\n\n"
                    "SOURCES TO CHECK:\n[Recommended websites]"
                )
            },
            {
                "role": "user",
                "content": f"Search for: {query}"
            }
        ],
        max_tokens=1000
    )
    return response.choices[0].message.content

def summarize_website(url):
    print(f"\nAURA Web Search: Summarizing {url}")
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')

        # Get text content
        paragraphs = soup.find_all('p')
        text = ' '.join([p.get_text() for p in paragraphs[:10]])
        text = text[:2000]

        ai_response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are AURA Web Search Agent. "
                        "Summarize the website content clearly. "
                        "Format:\n"
                        "WEBSITE SUMMARY\n\n"
                        "MAIN TOPIC:\n[What the page is about]\n\n"
                        "KEY POINTS:\n"
                        "1. [Point]\n"
                        "2. [Point]\n"
                        "3. [Point]\n\n"
                        "CONCLUSION:\n[Main takeaway]"
                    )
                },
                {
                    "role": "user",
                    "content": f"Summarize this content: {text}"
                }
            ],
            max_tokens=800
        )
        return ai_response.choices[0].message.content

    except Exception as e:
        return f"Could not access website. Error: {str(e)}"