from groq import Groq
from config.settings import GROQ_API_KEY, MODEL_NAME

client = Groq(api_key=GROQ_API_KEY)

def create_resume(name, field, experience, skills, education):
    print(f"\nAURA Resume Agent: creating resume for {name}")

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are AURA Resume Agent, an expert career counselor. "
                    "Create a professional resume. "
                    "Format:\n"
                    "RESUME\n\n"
                    "[FULL NAME]\n"
                    "[Email] | [Phone] | [Location] | [LinkedIn]\n\n"
                    "PROFESSIONAL SUMMARY\n"
                    "[2-3 sentence compelling summary]\n\n"
                    "SKILLS\n"
                    "Technical: [skills]\n"
                    "Soft Skills: [skills]\n\n"
                    "WORK EXPERIENCE\n"
                    "[Job Title] | [Company] | [Date]\n"
                    "- [Achievement]\n"
                    "- [Achievement]\n\n"
                    "EDUCATION\n"
                    "[Degree] | [University] | [Year]\n\n"
                    "PROJECTS\n"
                    "[Project Name]\n"
                    "[Brief description]\n\n"
                    "CERTIFICATIONS\n"
                    "[Certification]\n\n"
                    "No markdown symbols."
                )
            },
            {
                "role": "user",
                "content": (
                    f"Create a professional resume for:\n"
                    f"Name: {name}\n"
                    f"Field: {field}\n"
                    f"Experience: {experience}\n"
                    f"Skills: {skills}\n"
                    f"Education: {education}"
                )
            }
        ],
        max_tokens=1500
    )
    return response.choices[0].message.content

def improve_resume(resume_text):
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are AURA Resume Agent. "
                    "Improve and enhance the given resume. "
                    "Format:\n"
                    "IMPROVED RESUME\n\n"
                    "[Enhanced resume content]\n\n"
                    "CHANGES MADE:\n"
                    "1. [Change]\n"
                    "2. [Change]\n"
                    "3. [Change]\n\n"
                    "TIPS:\n"
                    "1. [Tip to make resume stronger]\n"
                    "2. [Tip]"
                )
            },
            {"role": "user", "content": f"Improve this resume: {resume_text}"}
        ],
        max_tokens=1500
    )
    return response.choices[0].message.content

def get_resume_tips(field):
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are AURA Resume Agent. "
                    "Give specific resume tips for the field. "
                    "Format:\n"
                    "RESUME TIPS FOR: [field]\n\n"
                    "TOP 10 TIPS:\n"
                    "1. [Tip]\n"
                    "2. [Tip]\n"
                    "...\n\n"
                    "KEYWORDS TO INCLUDE:\n"
                    "[Industry keywords]\n\n"
                    "COMMON MISTAKES TO AVOID:\n"
                    "1. [Mistake]\n"
                    "2. [Mistake]"
                )
            },
            {"role": "user", "content": f"Give resume tips for: {field}"}
        ],
        max_tokens=800
    )
    return response.choices[0].message.content