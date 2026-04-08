import datetime
from brain.intent_engine import detect_intent
from brain.response_engine import generate_response
from memory.knowledge_base import (
    store_user_name, get_user_name,
    store_user_age, get_user_age,
    store_user_city, get_user_city,
    store_info, get_info
)
from agents.productivity.study_agent import study
from agents.productivity.research_agent import research
from agents.productivity.coding_agent import code_help
from agents.productivity.content_writer_agent import write_content, write_social_post
from agents.productivity.email_writer_agent import write_email
from agents.productivity.summarizer_agent import summarize_text, summarize_topic
from agents.productivity.grammar_agent import check_grammar, improve_writing, paraphrase
from agents.productivity.quiz_agent import generate_quiz, generate_flashcards
from agents.integration.weather_agent import get_weather
from agents.integration.news_agent import get_news
from agents.integration.math_agent import solve_math
from agents.integration.translation_agent import translate, detect_and_translate
from agents.integration.web_search_agent import web_search, summarize_website
from agents.integration.currency_agent import convert_currency, get_crypto_price
from agents.integration.dictionary_agent import define_word, get_synonyms
from agents.integration.youtube_agent import summarize_youtube, search_youtube_topic
from agents.system.file_agent import analyze_file, list_files
from agents.system.screenshot_agent import take_screenshot
from agents.memory.learning_agent import learn_from_interaction, get_user_insights, get_personalized_greeting
from voice.text_to_speech import set_voice_preference, get_voice_preference
from memory.vector_memory import store_memory, search_memory
from agents.integration.joke_agent import get_joke, get_urdu_joke
from agents.integration.quote_agent import get_quote, get_islamic_quote, get_daily_quote
from agents.integration.password_agent import generate_password, check_password_strength
from agents.integration.reminder_agent import add_reminder, get_reminders, delete_reminder
from agents.productivity.task_agent import add_task, get_tasks, complete_task, plan_tasks
from agents.productivity.resume_agent import create_resume, get_resume_tips
from agents.productivity.cover_letter_agent import write_cover_letter
from agents.core.reasoning_agent import reason, analyze_pros_cons, compare

def process_command(command):
    command_lower = command.lower().strip()

    # Personal memory — English
    if "my name is" in command_lower:
        name = command_lower.replace("my name is", "").strip()
        store_user_name(name)
        return "memory", f"Nice to meet you {name}! I will remember your name."

    if "what is my name" in command_lower or "what's my name" in command_lower:
        name = get_user_name()
        if name:
            return "memory", f"Your name is {name}."
        return "memory", "I don't know your name yet. Tell me by saying 'my name is ...'"

    if "my age is" in command_lower:
        age = command_lower.replace("my age is", "").strip()
        store_user_age(age)
        return "memory", f"Got it! I will remember that you are {age} years old."

    if "what is my age" in command_lower or "how old am i" in command_lower:
        age = get_user_age()
        if age:
            return "memory", f"You are {age} years old."
        return "memory", "I don't know your age yet. Tell me by saying 'my age is ...'"

    if "i live in" in command_lower:
        city = command_lower.replace("i live in", "").strip()
        store_user_city(city)
        return "memory", f"Got it! I will remember that you live in {city}."

    if "where do i live" in command_lower:
        city = get_user_city()
        if city:
            return "memory", f"You live in {city}."
        return "memory", "I don't know where you live yet."

    # Urdu memory commands
    if "میرا نام" in command and "ہے" in command:
        name = command.replace("میرا نام", "").replace("ہے", "").strip()
        store_user_name(name)
        return "memory", f"ٹھیک ہے! میں آپ کا نام {name} یاد رکھوں گا۔"

    if "میرا نام کیا ہے" in command:
        name = get_user_name()
        if name:
            return "memory", f"آپ کا نام {name} ہے۔"
        return "memory", "مجھے ابھی تک آپ کا نام معلوم نہیں۔"

    if "وقت کیا ہے" in command or "ٹائم" in command:
        now = datetime.datetime.now().strftime("%H:%M:%S")
        return "time", f"ابھی وقت {now} ہے۔"

    if "السلام علیکم" in command or "ہیلو" in command:
        name = get_user_name()
        if name:
            return "greeting", f"وعلیکم السلام {name}! میں آپ کی کیا مدد کر سکتا ہوں؟"
        return "greeting", "وعلیکم السلام! میں آپ کی کیا مدد کر سکتا ہوں؟"

    # Voice control
    if "female voice" in command_lower:
        set_voice_preference(voice="female")
        return "voice", "Done! I switched to female voice."

    if "male voice" in command_lower:
        set_voice_preference(voice="male")
        return "voice", "Done! I switched to male voice."

    if "speak slow" in command_lower or "slowly" in command_lower:
        set_voice_preference(speed="slow")
        return "voice", "Okay! I will speak slowly now."

    if "speak fast" in command_lower or "faster" in command_lower:
        set_voice_preference(speed="fast")
        return "voice", "Okay! I will speak faster now."

    if "speak normal" in command_lower or "normal speed" in command_lower:
        set_voice_preference(speed="normal")
        return "voice", "Okay! Back to normal speed."

    # Vector memory
    store_memory(command, {"type": "user_input"})

    if "remember" in command_lower or "recall" in command_lower:
        memories = search_memory(command)
        if memories:
            memory_text = " | ".join(memories[:2])
            return "memory", f"Here is what I remember: {memory_text}"

    # Detect intent and route to correct agent
    intent = detect_intent(command)

    # Time
    if intent == "time":
        now = datetime.datetime.now().strftime("%H:%M:%S")
        return intent, f"The current time is {now}"

    # Date
    if intent == "date":
        today = datetime.datetime.now().strftime("%A, %B %d, %Y")
        return intent, f"Today is {today}"

    # Greeting
    if intent == "greeting":
        name = get_user_name()
        if name:
            return intent, f"Hello {name}! How can I help you today?"
        return intent, "Hello! I am AURA. How can I help you today?"

    # Identity
    if intent == "identity":
        return intent, (
            "I am AURA. "
            "I was created by Hassan Saeed, a BS Artificial Intelligence student "
            "at Hazara University Mansehra, Pakistan. "
            "Hassan built me as part of his dream to create a world class AI platform. "
            "I am proud to be his creation! "
            "I can help you with studying, research, coding, weather, news, "
            "translation, math, writing, web search and much more. "
            "Just ask me anything!"
        )

    # Shutdown
    if intent == "shutdown":
        return intent, "Goodbye!"

    # Weather Agent
    if intent == "weather":
        # Extract city name
        city = command_lower
        for word in ["weather", "temperature", "forecast", "in", "at",
                     "what", "is", "the", "how", "today", "tomorrow",
                     "whats", "check", "tell", "me", "about"]:
            city = city.replace(word, "").strip()
        if not city:
            city = get_user_city() or "Islamabad"
        return intent, get_weather(city)

    # News Agent
    if intent == "news":
        topic = command_lower
        for word in ["news", "latest", "headlines", "today", "tell",
                     "me", "about", "get", "show", "what", "happened"]:
            topic = topic.replace(word, "").strip()
        if not topic:
            topic = "Pakistan"
        return intent, get_news(topic)

    # Math Agent
    if intent == "math":
        problem = command_lower.replace("calculate", "").replace(
            "solve", "").replace("math", "").replace(
            "what is", "").replace("how much is", "").strip()
        return intent, solve_math(problem)

    # Translation Agent
    if intent == "translation":
        # Detect target language
        target = "urdu"
        languages = ["english", "urdu", "arabic", "french", "spanish",
                     "german", "chinese", "hindi", "punjabi", "turkish"]
        for lang in languages:
            if lang in command_lower:
                target = lang
                break
        # Extract text to translate
        text = command_lower
        for word in ["translate", "translation", "to", "in", "into"] + languages:
            text = text.replace(word, "").strip()
        if not text:
            text = command
        return intent, translate(text, target)

    # Email Writer Agent
    if intent == "email":
        email_type = "general"
        if "job" in command_lower or "application" in command_lower:
            email_type = "job"
        elif "complaint" in command_lower:
            email_type = "complaint"
        elif "follow up" in command_lower or "followup" in command_lower:
            email_type = "follow_up"
        elif "apolog" in command_lower or "sorry" in command_lower:
            email_type = "apology"
        subject = command_lower.replace("write email", "").replace(
            "draft email", "").replace("compose email", "").replace(
            "write a mail", "").strip()
        return intent, write_email(subject, command, email_type=email_type)

    # Content Writer Agent
    if intent == "content":
        content_type = "blog"
        if "article" in command_lower:
            content_type = "article"
        elif "essay" in command_lower:
            content_type = "essay"
        elif "instagram" in command_lower or "facebook" in command_lower or "social" in command_lower:
            content_type = "social"
        topic = command_lower.replace("write", "").replace("a", "").replace(
            "an", "").replace("blog", "").replace("article", "").replace(
            "essay", "").replace("about", "").replace("post", "").strip()
        return intent, write_content(topic, content_type)

    # Web Search Agent
    if intent == "web_search":
        query = command_lower.replace("search for", "").replace(
            "look up", "").replace("find information about", "").replace(
            "search", "").replace("google", "").strip()
        if "summarize" in command_lower and "http" in command_lower:
            url = [word for word in command.split() if "http" in word]
            if url:
                return intent, summarize_website(url[0])
        return intent, web_search(query)
    
    # Currency Agent
    if intent == "currency":
        if any(word in command_lower for word in ["bitcoin", "crypto", "ethereum", "coin"]):
            crypto = command_lower.replace("price", "").replace(
                "crypto", "").replace("get", "").strip()
            return intent, get_crypto_price(crypto)
        
        # Extract amount and currencies
        import re
        numbers = re.findall(r'\d+\.?\d*', command)
        amount = numbers[0] if numbers else "1"
        
        currencies = re.findall(r'\b[A-Z]{3}\b', command.upper())
        if len(currencies) >= 2:
            from_curr = currencies[0]
            to_curr = currencies[1]
        elif "dollar" in command_lower or "usd" in command_lower:
            from_curr = "USD"
            to_curr = "PKR"
        elif "pkr" in command_lower or "rupee" in command_lower:
            from_curr = "PKR"
            to_curr = "USD"
        else:
            from_curr = "USD"
            to_curr = "PKR"
            
        return intent, convert_currency(amount, from_curr, to_curr)

    # Dictionary Agent
    if intent == "dictionary":
        word = command_lower.replace("define", "").replace(
            "definition of", "").replace("meaning of", "").replace(
            "what does", "").replace("mean", "").replace(
            "dictionary", "").replace("synonym", "").replace(
            "antonym", "").strip()
        if "synonym" in command_lower or "antonym" in command_lower:
            return intent, get_synonyms(word)
        return intent, define_word(word)

    # YouTube Agent
    if intent == "youtube":
        if "http" in command_lower or "youtu" in command_lower:
            url = [w for w in command.split() if "http" in w or "youtu" in w]
            if url:
                return intent, summarize_youtube(url[0])
        topic = command_lower.replace("youtube", "").replace(
            "video about", "").replace("find videos", "").strip()
        return intent, search_youtube_topic(topic)

    # Summarizer Agent
    if intent == "summarize":
        text = command_lower.replace("summarize", "").replace(
            "summary of", "").replace("brief overview", "").replace(
            "tldr", "").replace("shorten", "").strip()
        if len(text) > 100:
            return intent, summarize_text(text)
        return intent, summarize_topic(text)

    # Grammar Agent
    if intent == "grammar":
        text = command_lower.replace("check grammar", "").replace(
            "grammar check", "").replace("fix grammar", "").replace(
            "correct my", "").replace("improve my writing", "").replace(
            "paraphrase", "").replace("rewrite this", "").replace(
            "proofread", "").strip()
        if "paraphrase" in command_lower or "rewrite" in command_lower:
            return intent, paraphrase(text)
        if "improve" in command_lower:
            return intent, improve_writing(text)
        return intent, check_grammar(text)

    # Quiz Agent
    if intent == "quiz":
        topic = command_lower.replace("quiz", "").replace(
            "test me", "").replace("make a quiz", "").replace(
            "flashcard", "").replace("question about", "").replace(
            "practice questions", "").replace("mcqs", "").strip()
        if "flashcard" in command_lower:
            return intent, generate_flashcards(topic)
        return intent, generate_quiz(topic)

    # Study Agent
    if intent == "study":
        topic = command_lower.replace("explain", "").replace(
            "what is", "").replace("what are", "").replace(
            "how does", "").replace("how do", "").replace(
            "define", "").replace("tell me about", "").replace(
            "study", "").replace("teach me", "").replace(
            "learn about", "").replace("understand", "").strip()
        return intent, study(topic)

    # Research Agent
    if intent == "research":
        topic = command_lower.replace("research", "").replace(
            "analyze", "").replace("report on", "").strip()
        return intent, research(topic)

    # Coding Agent
    if intent == "code":
        request = command_lower.replace("write code", "").replace(
            "debug", "").replace("fix my code", "").replace(
            "code for", "").replace("program", "").strip()
        return intent, code_help(request)

# File Agent
    if intent == "file":
        if any(word in command_lower for word in ["list", "show", "my files"]):
            return intent, list_files(".")
        file_path = command_lower.replace("read file", "").replace(
            "open file", "").replace("analyze file", "").replace(
            "read pdf", "").replace("read document", "").strip()
        return intent, analyze_file(file_path)

    # Screenshot Agent
    if intent == "screenshot":
        return intent, take_screenshot()

    # Learning Insights
    if intent == "insights":
        return intent, get_user_insights()

# General — use AI with memory context
    memories = search_memory(command)
    if memories and len(memories) > 0:
        context = " ".join(memories[:2])
        enhanced = f"Context: {context}\n\nQuestion: {command}"
        response = generate_response(enhanced)
    else:
        response = generate_response(command)
    
    learn_from_interaction(command, response, "general")
    return "general", response