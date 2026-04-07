def detect_intent(command):
    command_lower = command.lower().strip()
    words = command_lower.split()

    # Time
    if any(word in words for word in ["time", "clock"]):
        return "time"

    # Date
    if any(word in words for word in ["date", "today"]):
        return "date"

    # Greeting — exact words only
    if command_lower in ["hi", "hello", "hey", "hey aura", "hi aura", "hello aura"]:
        return "greeting"

    # Shutdown
    if any(word in words for word in ["bye", "exit", "quit", "shutdown"]):
        return "shutdown"

    # Identity
    if "your name" in command_lower or "who are you" in command_lower:
        return "identity"

    # Weather
    if "weather" in command_lower:
        return "weather"

    # Joke
    if "joke" in command_lower:
        return "joke"

    # Study
    if any(phrase in command_lower for phrase in ["study", "explain", "teach me", "what is", "what are", "how does", "how do", "define", "tell me about", "learn about"]):
        return "study"

    # Research
    if any(phrase in command_lower for phrase in ["research", "look up", "search for", "find information"]):
        return "research"

    # Code
    if any(phrase in command_lower for phrase in ["write code", "help me code", "debug", "fix my code", "program"]):
        return "code"

    return "general"