import re
import requests
from groq import Groq
from config.settings import GROQ_API_KEY, MODEL_NAME
from memory.vector_memory import store_memory


client = Groq(api_key=GROQ_API_KEY)


def clean(text):
    if not text:
        return "I couldn't analyze the YouTube content right now."

    text = str(text)
    text = re.sub(r"\*{1,3}(.*?)\*{1,3}", r"\1", text)
    text = re.sub(r"#{1,6}\s*", "", text)
    text = re.sub(r"`{3}[\w]*\n?", "", text)
    text = re.sub(r"`(.+?)`", r"\1", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_video_id(url):
    url = url.strip()

    if "youtube.com/watch?v=" in url:
        return url.split("v=")[1].split("&")[0]

    if "youtu.be/" in url:
        return url.split("youtu.be/")[1].split("?")[0]

    return None


def summarize_youtube(url):
    video_id = extract_video_id(url)

    if not video_id:
        return "Please provide a valid YouTube URL."

    try:
        oembed_url = "https://www.youtube.com/oembed"
        response = requests.get(
            oembed_url,
            params={"url": url, "format": "json"},
            timeout=10
        )
        response.raise_for_status()
        data = response.json()

        title = data.get("title", "Unknown")
        author = data.get("author_name", "Unknown")

        ai_response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are AURA YouTube Agent. "
                        "Based on the video title and channel, infer what the video is likely about in plain text.\n\n"
                        "Structure:\n"
                        "VIDEO TITLE\n"
                        "CHANNEL\n"
                        "LIKELY CONTENT\n"
                        "KEY TOPICS\n"
                        "WHO SHOULD WATCH\n"
                        "NOTE\n\n"
                        "Do not use markdown symbols like *, #, or backticks."
                    )
                },
                {
                    "role": "user",
                    "content": (
                        f"Analyze this YouTube video:\n"
                        f"Title: {title}\n"
                        f"Channel: {author}\n"
                        f"URL: {url}"
                    )
                }
            ],
            max_tokens=650,
            temperature=0.3
        )

        result = ai_response.choices[0].message.content if ai_response.choices else ""
        cleaned = clean(result)

        store_memory(
            f"YouTube analyzed: {title}",
            {
                "type": "youtube_summary",
                "video_id": video_id,
                "channel": author
            }
        )

        return cleaned

    except Exception as e:
        return f"Could not analyze video. Error: {str(e)}"


def search_youtube_topic(topic):
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are AURA YouTube Agent. "
                        "Recommend useful YouTube search terms and video-learning strategy in plain text.\n\n"
                        "Structure:\n"
                        "TOPIC\n"
                        "RECOMMENDED SEARCHES\n"
                        "BEST CHANNEL TYPES\n"
                        "LEARNING PATH\n"
                        "WATCHING TIPS\n\n"
                        "Do not use markdown symbols like *, #, or backticks."
                    )
                },
                {
                    "role": "user",
                    "content": f"Find YouTube videos about: {topic}"
                }
            ],
            max_tokens=550,
            temperature=0.4
        )

        result = response.choices[0].message.content if response.choices else ""
        cleaned = clean(result)

        store_memory(
            f"YouTube topic searched: {topic}",
            {
                "type": "youtube_search"
            }
        )

        return cleaned

    except Exception as e:
        return f"YouTube search error: {str(e)}"