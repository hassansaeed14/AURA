from groq import Groq
from config.settings import GROQ_API_KEY, MODEL_NAME

client = Groq(api_key=GROQ_API_KEY)

def write_content(topic, content_type="blog", tone="professional", word_count=500):
    print(f"\nAURA Content Writer: {content_type} about {topic}")

    content_formats = {
        "blog": (
            "BLOG POST TITLE: [Engaging title]\n\n"
            "INTRODUCTION:\n[Hook the reader]\n\n"
            "MAIN BODY:\n"
            "Section 1: [Heading]\n[Content]\n\n"
            "Section 2: [Heading]\n[Content]\n\n"
            "Section 3: [Heading]\n[Content]\n\n"
            "CONCLUSION:\n[Summary and call to action]\n\n"
            "TAGS: [relevant tags]"
        ),
        "article": (
            "ARTICLE TITLE: [Title]\n\n"
            "ABSTRACT:\n[Brief summary]\n\n"
            "1. INTRODUCTION\n[Introduction]\n\n"
            "2. MAIN CONTENT\n[Detailed content]\n\n"
            "3. ANALYSIS\n[Analysis]\n\n"
            "4. CONCLUSION\n[Conclusion]\n\n"
            "REFERENCES: [if applicable]"
        ),
        "social": (
            "SOCIAL MEDIA POST:\n\n"
            "CAPTION:\n[Engaging caption]\n\n"
            "HASHTAGS:\n[Relevant hashtags]\n\n"
            "CALL TO ACTION:\n[What should audience do]"
        ),
        "essay": (
            "ESSAY TITLE: [Title]\n\n"
            "THESIS STATEMENT:\n[Main argument]\n\n"
            "INTRODUCTION:\n[Background and thesis]\n\n"
            "BODY PARAGRAPH 1:\n[First argument]\n\n"
            "BODY PARAGRAPH 2:\n[Second argument]\n\n"
            "BODY PARAGRAPH 3:\n[Third argument]\n\n"
            "CONCLUSION:\n[Restate thesis and summarize]\n\n"
            "WORD COUNT: approximately {word_count} words"
        )
    }

    format_template = content_formats.get(content_type, content_formats["blog"])

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": (
                    f"You are AURA Content Writer Agent, an expert writer. "
                    f"Write {content_type} content with a {tone} tone. "
                    f"Write approximately {word_count} words. "
                    f"Use this format:\n{format_template}\n"
                    f"No markdown symbols like * or #. Use plain text."
                )
            },
            {
                "role": "user",
                "content": f"Write a {content_type} about: {topic}"
            }
        ],
        max_tokens=2000
    )
    return response.choices[0].message.content

def write_social_post(topic, platform="instagram"):
    print(f"\nAURA Content Writer: {platform} post about {topic}")

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": (
                    f"You are AURA Social Media Expert. "
                    f"Write an engaging {platform} post. "
                    f"Format:\n"
                    f"POST CAPTION:\n[Engaging caption optimized for {platform}]\n\n"
                    f"HASHTAGS:\n[10-15 relevant hashtags]\n\n"
                    f"BEST TIME TO POST:\n[When to post for maximum engagement]\n\n"
                    f"ENGAGEMENT TIP:\n[How to boost engagement]"
                )
            },
            {
                "role": "user",
                "content": f"Write a {platform} post about: {topic}"
            }
        ],
        max_tokens=800
    )
    return response.choices[0].message.content