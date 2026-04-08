import requests
from groq import Groq
from config.settings import GROQ_API_KEY, MODEL_NAME

client = Groq(api_key=GROQ_API_KEY)

def summarize_youtube(url):
    print(f"\nAURA YouTube Agent: {url}")

    # Extract video ID
    video_id = None
    if "youtube.com/watch?v=" in url:
        video_id = url.split("v=")[1].split("&")[0]
    elif "youtu.be/" in url:
        video_id = url.split("youtu.be/")[1].split("?")[0]

    if not video_id:
        return "Please provide a valid YouTube URL."

    try:
        # Get video info using oEmbed
        oembed_url = f"https://www.youtube.com/oembed?url={url}&format=json"
        response = requests.get(oembed_url, timeout=10)
        data = response.json()

        title = data.get('title', 'Unknown')
        author = data.get('author_name', 'Unknown')

        # Use AI to provide summary based on title
        ai_response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are AURA YouTube Agent. "
                        "Based on the video title and channel, provide what this video is likely about. "
                        "Format:\n"
                        "VIDEO TITLE: [title]\n"
                        "CHANNEL: [channel name]\n\n"
                        "LIKELY CONTENT:\n[What this video is about]\n\n"
                        "KEY TOPICS:\n"
                        "1. [Topic]\n"
                        "2. [Topic]\n"
                        "3. [Topic]\n\n"
                        "WHO SHOULD WATCH:\n[Target audience]\n\n"
                        "NOTE: For full transcript analysis, premium features required."
                    )
                },
                {
                    "role": "user",
                    "content": f"Analyze this YouTube video: Title: {title}, Channel: {author}, URL: {url}"
                }
            ],
            max_tokens=600
        )
        return ai_response.choices[0].message.content

    except Exception as e:
        return f"Could not analyze video. Please check the URL. Error: {str(e)}"

def search_youtube_topic(topic):
    print(f"\nAURA YouTube Agent: searching {topic}")

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are AURA YouTube Agent. "
                    "Recommend YouTube search terms and types of videos for the given topic. "
                    "Format:\n"
                    "TOPIC: [topic]\n\n"
                    "RECOMMENDED SEARCHES:\n"
                    "1. [Search term]\n"
                    "2. [Search term]\n"
                    "3. [Search term]\n\n"
                    "BEST CHANNELS:\n"
                    "[Recommend relevant YouTube channels]\n\n"
                    "LEARNING PATH:\n"
                    "[Suggested order to watch videos]"
                )
            },
            {"role": "user", "content": f"Find YouTube videos about: {topic}"}
        ],
        max_tokens=500
    )
    return response.choices[0].message.content