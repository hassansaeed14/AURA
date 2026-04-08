def detect_intent(command):
    command_lower = command.lower().strip()
    words = command_lower.split()

    # Dictionary — MUST be first before study
    if command_lower.startswith("define ") or any(phrase in command_lower for phrase in [
        "definition of", "meaning of", "dictionary",
        "synonym of", "antonym of", "word meaning",
        "what does", "mean in english"
    ]):
        return "dictionary"

    # Weather
    if any(phrase in command_lower for phrase in [
        "weather", "temperature", "forecast", "rain", "sunny",
        "cloudy", "humid", "wind", "storm", "climate today",
        "how hot", "how cold", "what's the weather", "موسم"
    ]):
        return "weather"

    # News
    if any(phrase in command_lower for phrase in [
        "news", "latest", "headlines", "what happened",
        "current events", "today's news", "breaking",
        "خبریں", "آج کی خبر"
    ]):
        return "news"

    # Math
    if any(phrase in command_lower for phrase in [
        "calculate", "solve", "math", "equation", "algebra",
        "geometry", "calculus", "percentage", "square root",
        "multiply", "divide", "add", "subtract", "how much is",
        "what is", "=", "+", "-", "*", "/"
    ]) and any(char.isdigit() for char in command_lower):
        return "math"

    # Translation
    if any(phrase in command_lower for phrase in [
        "translate", "translation", "in urdu", "in english",
        "in arabic", "in french", "in spanish", "in hindi",
        "in punjabi", "in turkish", "in chinese", "in german",
        "ترجمہ", "translate this", "how to say"
    ]):
        return "translation"

    # Email writing
    if any(phrase in command_lower for phrase in [
        "write email", "draft email", "compose email",
        "email to", "send email", "write a mail",
        "professional email", "job email", "complaint email",
        "follow up email", "apology email"
    ]):
        return "email"

    # Content writing
    if any(phrase in command_lower for phrase in [
        "write a blog", "write an article", "write a post",
        "write an essay", "write content", "social media post",
        "instagram post", "facebook post", "twitter post",
        "write for me", "content about", "create content"
    ]):
        return "content"

    # Web search
    if any(phrase in command_lower for phrase in [
        "search for", "look up", "find information",
        "search the web", "google", "what is the latest",
        "summarize website", "browse", "internet search"
    ]):
        return "web_search"

    # Coding
    if any(phrase in command_lower for phrase in [
        "write code", "debug", "fix my code", "programming",
        "python code", "javascript", "error in code",
        "how to code", "code for", "function for",
        "algorithm", "write a program", "code help"
    ]):
        return "code"

    # Study - only for detailed requests
    if any(phrase in command_lower for phrase in [
        "explain in detail", "tell me everything about",
        "write about", "study guide", "teach me about",
        "assignment on", "essay on", "detailed explanation"
    ]):
        return "study"

    # Research
    if any(phrase in command_lower for phrase in [
        "research", "analyze", "investigation",
        "report on", "findings about", "data on",
        "statistics", "study on", "academic"
    ]):
        return "research"

    # Time
    if any(word in words for word in ["time", "clock", "what time"]):
        return "time"

    # Date
    if any(word in words for word in ["date", "today", "day"]):
        return "date"

    # Greeting
    if command_lower in ["hi", "hello", "hey", "hey aura",
                         "hi aura", "hello aura", "good morning",
                         "good evening", "good afternoon", "salam",
                         "السلام علیکم", "ہیلو"]:
        return "greeting"

    # Identity
    if any(phrase in command_lower for phrase in [
        "your name", "who are you", "what are you",
        "about yourself", "introduce yourself"
    ]):
        return "identity"

    # Shutdown
    if any(word in words for word in ["bye", "exit", "quit", "shutdown", "goodbye"]) or \
       any(phrase in command_lower for phrase in ["bye bye", "bye-bye", "good bye", "see you"]):
        return "shutdown"

# Currency & Crypto
    if any(phrase in command_lower for phrase in [
        "convert currency", "exchange rate", "currency",
        "usd to", "pkr to", "dollar to", "rupee to",
        "bitcoin", "crypto", "ethereum", "coin price"
    ]):
        return "currency"

    # Dictionary — check BEFORE study
    if any(phrase in command_lower for phrase in [
        "define ", "definition of", "meaning of",
        "dictionary", "synonym of", "antonym of",
        "word meaning", "what does", "mean in english"
    ]):
        return "dictionary"

    # YouTube
    if any(phrase in command_lower for phrase in [
        "youtube", "youtu.be", "video about",
        "summarize video", "youtube video"
    ]):
        return "youtube"

    # Summarizer
    if any(phrase in command_lower for phrase in [
        "summarize", "summary of", "brief overview",
        "tldr", "shorten", "condense", "in short"
    ]):
        return "summarize"

    # Grammar
    if any(phrase in command_lower for phrase in [
        "check grammar", "grammar check", "fix grammar",
        "correct my", "improve my writing", "paraphrase",
        "rewrite this", "proofread"
    ]):
        return "grammar"

    # Quiz
    if any(phrase in command_lower for phrase in [
        "quiz", "test me", "make a quiz", "flashcard",
        "question about", "practice questions", "mcqs"
    ]):
        return "quiz"
    
  # File operations
    if any(phrase in command_lower for phrase in [
        "read file", "open file", "analyze file",
        "read pdf", "open pdf", "list files",
        "show files", "what files", "read document",
        "list of my files", "show my files",
        "files in", "my files"
    ]):
        return "file"

    # Screenshot
    if any(phrase in command_lower for phrase in [
        "take screenshot", "screenshot", "capture screen",
        "screen capture", "take a picture of screen"
    ]):
        return "screenshot"

    # Learning insights
    if any(phrase in command_lower for phrase in [
        "what have you learned", "my usage", "my insights",
        "how often do i", "my patterns", "what do i use most",
        "what do i use", "my statistics", "how many times",
        "my activity", "usage report"
    ]):
        return "insights"
    
    # Joke
    if any(phrase in command_lower for phrase in [
        "tell me a joke", "joke", "make me laugh",
        "funny", "lطیفہ", "مزاحیہ"
    ]):
        return "joke"

    # Quote
    if any(phrase in command_lower for phrase in [
        "quote", "inspire me", "motivation", "motivational",
        "islamic quote", "daily quote", "give me a quote"
    ]):
        return "quote"

    # Password
    if any(phrase in command_lower for phrase in [
        "generate password", "create password", "password generator",
        "strong password", "check password", "password strength"
    ]):
        return "password"

    # Reminder
    if any(phrase in command_lower for phrase in [
        "remind me", "set reminder", "add reminder",
        "my reminders", "show reminders", "delete reminder"
    ]):
        return "reminder"

    # Task
    if any(phrase in command_lower for phrase in [
        "add task", "my tasks", "show tasks", "complete task",
        "delete task", "task list", "plan my", "to do",
        "todo", "task plan"
    ]):
        return "task"

    # Resume
    if any(phrase in command_lower for phrase in [
        "create resume", "write resume", "make resume",
        "resume tips", "improve resume", "cv"
    ]):
        return "resume"

    # Cover letter
    if any(phrase in command_lower for phrase in [
        "cover letter", "write cover letter",
        "job application letter", "application letter"
    ]):
        return "cover_letter"

    # Compare / Pros Cons
    if any(phrase in command_lower for phrase in [
        "compare", "vs", "versus", "pros and cons",
        "difference between", "which is better"
    ]):
        return "compare"
    
    return "general"