import re
import requests
from bs4 import BeautifulSoup
from groq import Groq
from config.settings import GROQ_API_KEY, MODEL_NAME
from memory.vector_memory import store_memory


client = Groq(api_key=GROQ_API_KEY)


def clean(text):
    if not text:
        return "I couldn't get search results right now."

    text = str(text)
    text = re.sub(r"\*{1,3}(.*?)\*{1,3}", r"\1", text)
    text = re.sub(r"#{1,6}\s*", "", text)
    text = re.sub(r"`{3}[\w]*\n?", "", text)
    text = re.sub(r"`(.+?)`", r"\1", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def web_search(query):
    try:
        url = "https://api.duckduckgo.com/"
        response = requests.get(
            url,
            params={
                "q": query,
                "format": "json",
                "no_html": 1,
                "skip_disambig": 1
            },
            timeout=10
        )
        response.raise_for_status()
        data = response.json()

        result = f"WEB SEARCH RESULTS FOR: {query}\n\n"

        if data.get("Heading"):
            result += f"Topic: {data['Heading']}\n\n"

        if data.get("Abstract"):
            result += f"Summary:\n{data['Abstract']}\n\n"

        related = data.get("RelatedTopics", [])
        collected = []

        for item in related:
            if isinstance(item, dict) and item.get("Text"):
                collected.append(item["Text"])
            elif isinstance(item, dict) and item.get("Topics"):
                for sub in item["Topics"]:
                    if isinstance(sub, dict) and sub.get("Text"):
                        collected.append(sub["Text"])

            if len(collected) >= 5:
                break

        if collected:
            result += "Related Information:\n"
            for i, text in enumerate(collected[:5], 1):
                result += f"{i}. {text}\n\n"

        if len(result.strip()) < 80:
            return search_with_ai(query)

        store_memory(
            f"Web searched: {query}",
            {
                "type": "web_search",
                "query": query
            }
        )

        return result.strip()

    except Exception:
        return search_with_ai(query)


def search_with_ai(query):
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are AURA Web Search Agent. "
                        "Provide a useful search-style response in plain text.\n\n"
                        "Structure:\n"
                        "SEARCH RESULTS FOR\n"
                        "TOP RESULT\n"
                        "KEY FACTS\n"
                        "ADDITIONAL INFO\n"
                        "SOURCES TO CHECK\n\n"
                        "Do not use markdown symbols like *, #, or backticks."
                    )
                },
                {
                    "role": "user",
                    "content": f"Search for: {query}"
                }
            ],
            max_tokens=1000,
            temperature=0.3
        )

        result = response.choices[0].message.content if response.choices else ""
        cleaned = clean(result)

        store_memory(
            f"AI search fallback: {query}",
            {
                "type": "web_search_fallback",
                "query": query
            }
        )

        return cleaned

    except Exception as e:
        return f"Web Search Agent error: {str(e)}"


def summarize_website(url):
    try:
        response = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()

        soup = BeautifulSoup(response.content, "html.parser")

        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        paragraphs = soup.find_all("p")
        text = " ".join(p.get_text(" ", strip=True) for p in paragraphs[:12])
        text = re.sub(r"\s+", " ", text).strip()[:2500]

        if not text:
            return "I could not extract readable content from that website."

        ai_response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are AURA Web Search Agent. "
                        "Summarize website content clearly in plain text.\n\n"
                        "Structure:\n"
                        "WEBSITE SUMMARY\n"
                        "MAIN TOPIC\n"
                        "KEY POINTS\n"
                        "CONCLUSION\n\n"
                        "Do not use markdown symbols like *, #, or backticks."
                    )
                },
                {
                    "role": "user",
                    "content": f"Summarize this website content: {text}"
                }
            ],
            max_tokens=800,
            temperature=0.3
        )

        result = ai_response.choices[0].message.content if ai_response.choices else ""
        cleaned = clean(result)

        store_memory(
            f"Website summarized: {url}",
            {
                "type": "website_summary",
                "url": url
            }
        )

        return cleaned

    except Exception as e:
        return f"Could not access website. Error: {str(e)}"