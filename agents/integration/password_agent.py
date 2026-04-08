import secrets
import string
from memory.vector_memory import store_memory


SYMBOLS = "!@#$%^&*"


def generate_password(length=12, include_symbols=True, include_numbers=True):
    try:
        length = max(6, int(length))

        chars = string.ascii_letters
        if include_numbers:
            chars += string.digits
        if include_symbols:
            chars += SYMBOLS

        # 🔐 Use cryptographically secure generator
        password = ''.join(secrets.choice(chars) for _ in range(length))

        # Ensure at least one of each type
        password_list = list(password)

        if include_numbers:
            password_list[0] = secrets.choice(string.digits)
        if include_symbols:
            password_list[1] = secrets.choice(SYMBOLS)
        password_list[2] = secrets.choice(string.ascii_uppercase)
        password_list[3] = secrets.choice(string.ascii_lowercase)

        password = ''.join(password_list)

        # Strength calculation
        if length >= 14 and include_symbols and include_numbers:
            strength = "VERY STRONG"
        elif length >= 12:
            strength = "STRONG"
        elif length >= 8:
            strength = "MEDIUM"
        else:
            strength = "WEAK"

        store_memory(
            "Password generated",
            {
                "type": "password",
                "length": length,
                "strength": strength
            }
        )

        return (
            "PASSWORD GENERATED\n\n"
            f"Password: {password}\n"
            f"Length: {length} characters\n"
            f"Strength: {strength}\n\n"
            "SECURITY TIPS:\n"
            "1. Never share your password\n"
            "2. Use a password manager\n"
            "3. Use unique passwords for each account\n"
            "4. Enable 2FA wherever possible"
        )

    except Exception as e:
        return f"Password generation error: {str(e)}"


def check_password_strength(password):
    try:
        score = 0
        feedback = []

        if len(password) >= 12:
            score += 2
        elif len(password) >= 8:
            score += 1
        else:
            feedback.append("Use at least 12 characters.")

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

        if any(c in SYMBOLS for c in password):
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

        store_memory(
            "Password strength checked",
            {
                "type": "password_check",
                "strength": strength,
                "length": len(password)
            }
        )

        result = (
            "PASSWORD STRENGTH CHECK\n\n"
            f"Password: {'*' * len(password)}\n"
            f"Strength: {strength}\n"
            f"Score: {score}/7\n\n"
        )

        if feedback:
            result += "IMPROVEMENTS:\n"
            for i, tip in enumerate(feedback, 1):
                result += f"{i}. {tip}\n"
        else:
            result += "Your password is excellent."

        return result

    except Exception as e:
        return f"Password check error: {str(e)}"