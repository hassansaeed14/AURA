from groq import Groq
from config.settings import GROQ_API_KEY, MODEL_NAME
from memory.vector_memory import store_memory

client = Groq(api_key=GROQ_API_KEY)

def research(topic):
    print(f"\nAURA Research Agent activated for: {topic}")

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": """You are AURA's Research Agent.
                Research topics thoroughly using your knowledge.
                Structure: 1) Overview 2) Key Facts 3) Latest Developments 4) Conclusion
                Be detailed and accurate. Under 300 words.
                Never use symbols like *, #, ` in your response.
                Write in plain text with numbered points like 1. 2. 3."""
            },
            {
                "role": "user",
                "content": f"Research this topic thoroughly: {topic}"
            }
        ]
    )

    result = response.choices[0].message.content

    # Store research in vector memory so AURA learns
    store_memory(f"Research about {topic}: {result}", {
        "type": "research",
        "topic": topic
    })

    return result

def web_search_simulation(query):
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": """You are AURA's web search agent.
                Simulate searching the web for current information.
                Give accurate, up to date information.
                Format: Key findings as bullet points."""
            },
            {
                "role": "user",
                "content": f"Search the web for: {query}"
            }
        ]
    )

    result = response.choices[0].message.content

    # Store search results so AURA learns
    store_memory(f"Web search for {query}: {result}", {
        "type": "web_search",
        "query": query
    })

    return result