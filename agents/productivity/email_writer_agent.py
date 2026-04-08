from groq import Groq
from config.settings import GROQ_API_KEY, MODEL_NAME

client = Groq(api_key=GROQ_API_KEY)

def write_email(subject, context, tone="professional", email_type="general"):
    print(f"\nAURA Email Writer: {email_type} email about {subject}")

    email_formats = {
        "general": (
            "Subject: [Email subject]\n\n"
            "Dear [Recipient],\n\n"
            "Opening paragraph: [Purpose of email]\n\n"
            "Main body: [Detailed information]\n\n"
            "Closing paragraph: [Call to action or next steps]\n\n"
            "Kind regards,\n[Your name]"
        ),
        "job": (
            "Subject: Application for [Position]\n\n"
            "Dear Hiring Manager,\n\n"
            "Introduction: [Who you are and position applying for]\n\n"
            "Why you are interested: [Your motivation]\n\n"
            "Your qualifications: [Relevant skills and experience]\n\n"
            "Closing: [Request for interview]\n\n"
            "Sincerely,\n[Your name]"
        ),
        "complaint": (
            "Subject: Formal Complaint Regarding [Issue]\n\n"
            "Dear [Recipient],\n\n"
            "I am writing to formally complain about: [Issue]\n\n"
            "Details of the issue: [What happened]\n\n"
            "Impact: [How it affected you]\n\n"
            "Resolution requested: [What you want done]\n\n"
            "I look forward to your prompt response.\n\n"
            "Regards,\n[Your name]"
        ),
        "follow_up": (
            "Subject: Following Up on [Previous Discussion]\n\n"
            "Dear [Recipient],\n\n"
            "I hope this email finds you well.\n\n"
            "I am following up on: [Previous discussion]\n\n"
            "Current status: [What you need to know]\n\n"
            "Next steps: [What should happen next]\n\n"
            "Please let me know if you need any additional information.\n\n"
            "Best regards,\n[Your name]"
        ),
        "apology": (
            "Subject: Sincere Apology for [Incident]\n\n"
            "Dear [Recipient],\n\n"
            "I am writing to sincerely apologize for: [What happened]\n\n"
            "What went wrong: [Explanation]\n\n"
            "Impact acknowledgment: [How it affected them]\n\n"
            "How I will fix it: [Your plan]\n\n"
            "Prevention: [How you will prevent it happening again]\n\n"
            "Once again, I sincerely apologize.\n\n"
            "Regards,\n[Your name]"
        )
    }

    format_template = email_formats.get(email_type, email_formats["general"])

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": (
                    f"You are AURA Email Writer Agent, an expert business writer. "
                    f"Write a {tone} {email_type} email. "
                    f"Use this format:\n{format_template}\n"
                    f"Make it clear, concise and professional. "
                    f"No markdown symbols."
                )
            },
            {
                "role": "user",
                "content": f"Write a {email_type} email about: {subject}. Context: {context}"
            }
        ],
        max_tokens=1000
    )
    return response.choices[0].message.content