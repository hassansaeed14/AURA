import random
import string
from groq import Groq
from config.settings import GROQ_API_KEY, MODEL_NAME

client = Groq(api_key=GROQ_API_KEY)

def generate_password(length=12, include_symbols=True, include_numbers=True):
    print(f"\nAURA Password Agent: generating {length} char password")

    chars = string.ascii_letters
    if include_numbers:
        chars += string.digits
    if include_symbols:
        chars += "!@#$%^&*"

    password = ''.join(random.choice(chars) for _ in range(length))

    # Ensure at least one of each type
    if include_numbers:
        password = password[:length-2] + random.choice(string.digits) + password[length-1:]
    if include_symbols:
        password = password[:length-1] + random.choice("!@#$%^&*")

    strength = "STRONG" if length >= 12 and include_symbols else "MEDIUM" if length >= 8 else "WEAK"

    return (
        f"PASSWORD GENERATED\n\n"
        f"Password: {password}\n"
        f"Length: {length} characters\n"
        f"Strength: {strength}\n\n"
        f"SECURITY TIPS:\n"
        f"1. Never share your password with anyone\n"
        f"2. Use different passwords for each account\n"
        f"3. Store it in a password manager\n"
        f"4. Change it every 3-6 months"
    )

def check_password_strength(password):
    score = 0
    feedback = []

    if len(password) >= 12:
        score += 2
    elif len(password) >= 8:
        score += 1
    else:
        feedback.append("Password is too short. Use at least 12 characters.")

    if any(c.isupper() for c in password):
        score += 1
    else:
        feedback.append("Add uppercase letters.")

    if any(c.islower() for c in password):
        score += 1
    else:
        feedback.append("Add lowercase letters.")

    if any(c.isdigit() for c in password):
        score += 1
    else:
        feedback.append("Add numbers.")

    if any(c in "!@#$%^&*" for c in password):
        score += 2
    else:
        feedback.append("Add special characters like !@#$%^&*")

    if score >= 6:
        strength = "VERY STRONG"
    elif score >= 4:
        strength = "STRONG"
    elif score >= 3:
        strength = "MEDIUM"
    else:
        strength = "WEAK"

    result = (
        f"PASSWORD STRENGTH CHECK\n\n"
        f"Password: {'*' * len(password)}\n"
        f"Strength: {strength}\n"
        f"Score: {score}/7\n\n"
    )

    if feedback:
        result += "IMPROVEMENTS NEEDED:\n"
        for i, tip in enumerate(feedback, 1):
            result += f"{i}. {tip}\n"
    else:
        result += "Your password is excellent!"

    return result