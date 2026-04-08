from groq import Groq
from config.settings import GROQ_API_KEY, MODEL_NAME

client = Groq(api_key=GROQ_API_KEY)

def write_cover_letter(name, position, company, experience, skills):
    print(f"\nAURA Cover Letter Agent: {position} at {company}")

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are AURA Cover Letter Agent, an expert career coach. "
                    "Write a compelling cover letter. "
                    "Format:\n"
                    "[Your Name]\n"
                    "[Date]\n\n"
                    "Hiring Manager\n"
                    "[Company Name]\n\n"
                    "Dear Hiring Manager,\n\n"
                    "OPENING PARAGRAPH:\n"
                    "[Hook + position applying for + why interested]\n\n"
                    "BODY PARAGRAPH 1:\n"
                    "[Relevant experience and achievements]\n\n"
                    "BODY PARAGRAPH 2:\n"
                    "[Skills that match job requirements]\n\n"
                    "BODY PARAGRAPH 3:\n"
                    "[Why this company specifically]\n\n"
                    "CLOSING PARAGRAPH:\n"
                    "[Call to action + thank you]\n\n"
                    "Sincerely,\n"
                    "[Name]\n\n"
                    "No markdown symbols. Make it compelling and professional."
                )
            },
            {
                "role": "user",
                "content": (
                    f"Write a cover letter for:\n"
                    f"Name: {name}\n"
                    f"Position: {position}\n"
                    f"Company: {company}\n"
                    f"Experience: {experience}\n"
                    f"Skills: {skills}"
                )
            }
        ],
        max_tokens=1000
    )
    return response.choices[0].message.content