from groq import Groq
from config.settings import GROQ_API_KEY, MODEL_NAME

client = Groq(api_key=GROQ_API_KEY)

def summarize_text(text, summary_type="brief"):
    print(f"\nAURA Summarizer Agent: {summary_type} summary")

    formats = {
        "brief": (
            "BRIEF SUMMARY\n\n"
            "MAIN POINT:\n[One sentence summary]\n\n"
            "KEY POINTS:\n"
            "1. [Point]\n"
            "2. [Point]\n"
            "3. [Point]\n\n"
            "CONCLUSION:\n[What to take away]"
        ),
        "detailed": (
            "DETAILED SUMMARY\n\n"
            "OVERVIEW:\n[2-3 sentence overview]\n\n"
            "MAIN TOPICS:\n"
            "Topic 1: [Title]\n[Explanation]\n\n"
            "Topic 2: [Title]\n[Explanation]\n\n"
            "Topic 3: [Title]\n[Explanation]\n\n"
            "KEY INSIGHTS:\n[Important insights]\n\n"
            "CONCLUSION:\n[Final takeaway]"
        ),
        "bullet": (
            "BULLET POINT SUMMARY\n\n"
            "Main Idea: [Core concept]\n\n"
            "Key Points:\n"
            "- [Point 1]\n"
            "- [Point 2]\n"
            "- [Point 3]\n"
            "- [Point 4]\n"
            "- [Point 5]\n\n"
            "Action Items:\n"
            "- [What to do with this information]"
        )
    }

    format_template = formats.get(summary_type, formats["brief"])

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": (
                    f"You are AURA Summarizer Agent, an expert at condensing information. "
                    f"Summarize the given text clearly and accurately. "
                    f"Use this format:\n{format_template}\n"
                    f"No markdown symbols. Plain text only."
                )
            },
            {
                "role": "user",
                "content": f"Summarize this text ({summary_type}): {text}"
            }
        ],
        max_tokens=1000
    )
    return response.choices[0].message.content

def summarize_topic(topic):
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are AURA Summarizer Agent. "
                    "Give a comprehensive summary of the topic. "
                    "Format:\n"
                    "TOPIC SUMMARY: [topic]\n\n"
                    "WHAT IT IS:\n[Brief explanation]\n\n"
                    "KEY FACTS:\n"
                    "1. [Fact]\n"
                    "2. [Fact]\n"
                    "3. [Fact]\n\n"
                    "WHY IT MATTERS:\n[Importance]\n\n"
                    "QUICK TAKEAWAY:\n[One sentence summary]"
                )
            },
            {"role": "user", "content": f"Summarize this topic: {topic}"}
        ],
        max_tokens=800
    )
    return response.choices[0].message.content