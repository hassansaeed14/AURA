import re
from datetime import datetime

from brain.intent_engine import detect_intent_with_confidence
from brain.response_engine import generate_response
from brain.understanding_engine import clean_user_input, split_multi_intent
from brain.decision_engine import (
    should_fallback_to_general,
    should_use_agent,
    should_plan,
    should_add_low_confidence_note,
    should_treat_as_multi_command,
    format_multi_response
)

from memory.vector_memory import store_memory
from memory.knowledge_base import (
    store_user_name, get_user_name,
    store_user_age, get_user_age,
    store_user_city, get_user_city
)

from agents.memory.learning_agent import (
    learn_from_interaction,
    get_user_insights,
    get_personalized_greeting,
    build_context
)

from agents.core.self_improvement_agent import (
    log_failure,
    log_low_confidence,
    log_agent_error
)

from agents.core.reasoning_agent import reason, compare
from agents.core.language_agent import detect_language, respond_in_language

from agents.productivity.fitness_agent import get_workout_plan
from agents.productivity.study_agent import study
from agents.productivity.research_agent import research
from agents.productivity.coding_agent import code_help
from agents.productivity.content_writer_agent import write_content
from agents.productivity.email_writer_agent import write_email
from agents.productivity.summarizer_agent import summarize_topic
from agents.productivity.grammar_agent import check_grammar
from agents.productivity.quiz_agent import generate_quiz, generate_flashcards

from agents.integration.weather_agent import get_weather
from agents.integration.news_agent import get_news
from agents.integration.math_agent import solve_math
from agents.integration.translation_agent import translate
from agents.integration.web_search_agent import web_search
from agents.integration.currency_agent import convert_currency, get_crypto_price
from agents.integration.dictionary_agent import define_word, get_synonyms
from agents.integration.youtube_agent import search_youtube_topic
from agents.integration.joke_agent import get_joke
from agents.integration.quote_agent import get_quote

from agents.system.file_agent import analyze_file, list_files
from agents.system.screenshot_agent import take_screenshot

from agents.autonomous.planner_agent import create_plan
from agents.autonomous.executor import execute_plan
from agents.cognitive.cognitive_core import cognitive_process

# ✅ NEW TRUST ENGINE
from security.trust_engine import build_permission_response


PLANNING_INTENTS = {"research", "study", "task"}
GREETING_INPUTS = {"hi", "hello", "hey", "hey aura", "hi aura", "hello aura"}


# -----------------------------
# Utility Functions
# -----------------------------

def extract_currency_request(command: str):
    amount_match = re.search(r"(\d+(\.\d+)?)", command)
    currency_matches = re.findall(r"\b[A-Z]{3}\b", command.upper())

    amount = float(amount_match.group(1)) if amount_match else 1.0

    if len(currency_matches) >= 2:
        return amount, currency_matches[0], currency_matches[1]

    return amount, "USD", "PKR"


def extract_translation_target(command: str):
    command_lower = command.lower()

    language_map = {
        "urdu": "urdu",
        "english": "english",
        "arabic": "arabic",
        "french": "french",
        "spanish": "spanish",
        "hindi": "hindi",
        "punjabi": "punjabi"
    }

    for lang in language_map:
        if f"in {lang}" in command_lower or f"to {lang}" in command_lower:
            return language_map[lang]

    return "english"


def store_and_learn(user_input: str, response: str, intent: str, extra_metadata=None):
    metadata = {"type": "user_input", "intent": intent}
    if extra_metadata:
        metadata.update(extra_metadata)

    store_memory(user_input, metadata)
    learn_from_interaction(user_input, response, intent)


def route_quiz_command(command: str):
    if "flashcard" in command.lower():
        return generate_flashcards(command)
    return generate_quiz(command)


# -----------------------------
# Agent Router
# -----------------------------

AGENT_ROUTER = {
    "weather": lambda cmd: get_weather(cmd),
    "news": lambda cmd: get_news(cmd),
    "math": lambda cmd: solve_math(cmd),
    "fitness": lambda cmd: get_workout_plan(cmd),
    "translation": lambda cmd: translate(cmd, extract_translation_target(cmd)),
    "research": lambda cmd: research(cmd),
    "study": lambda cmd: study(cmd),
    "code": lambda cmd: code_help(cmd),
    "content": lambda cmd: write_content(cmd, "blog"),
    "email": lambda cmd: write_email(cmd, cmd),
    "summarize": lambda cmd: summarize_topic(cmd),
    "grammar": lambda cmd: check_grammar(cmd),
    "quiz": route_quiz_command,
    "dictionary": lambda cmd: define_word(cmd),
    "synonyms": lambda cmd: get_synonyms(cmd),
    "web_search": lambda cmd: web_search(cmd),
    "youtube": lambda cmd: search_youtube_topic(cmd),
    "currency": lambda cmd: convert_currency(*extract_currency_request(cmd)),
    "crypto": lambda cmd: get_crypto_price("bitcoin"),
    "joke": lambda cmd: get_joke(),
    "quote": lambda cmd: get_quote(),
    "file": lambda cmd: analyze_file(cmd),
    "list_files": lambda cmd: list_files("."),
    "screenshot": lambda cmd: take_screenshot(),
}


# -----------------------------
# Memory Handling (FIXED VERSION)
# -----------------------------

def handle_personal_memory(command: str):
    cmd = command.lower().strip()

    normalized = re.sub(r"^(hi|hey|hello)\s+", "", cmd).strip()
    normalized = re.sub(r"^(no\s+i\s+mean\s+|i\s+mean\s+)", "", normalized).strip()

    name_match = re.search(r"\bmy name is\s+([a-zA-Z ]{1,40})$", normalized)
    if name_match:
        name = name_match.group(1).strip().title()
        store_user_name(name)
        return "memory", f"Nice to meet you {name}!"

    if "what is my name" in normalized:
        name = get_user_name()
        return "memory", f"Your name is {name}." if name else "I don't know your name yet."

    return None


# -----------------------------
# Core Processing
# -----------------------------

def process_single_command(command: str):
    raw_command = clean_user_input(command)
    command_lower = raw_command.lower()

    if not raw_command:
        return "general", "Please type something."

    if command_lower in GREETING_INPUTS:
        response = get_personalized_greeting()
        store_and_learn(raw_command, response, "greeting")
        return "greeting", response

    memory_response = handle_personal_memory(raw_command)
    if memory_response:
        store_and_learn(raw_command, memory_response[1], memory_response[0])
        return memory_response

    language = detect_language(raw_command)

    intent, confidence = detect_intent_with_confidence(raw_command)

    # 🔐 TRUST CHECK
    permission = build_permission_response(intent)

    if not permission["success"]:
        return "permission", permission["permission"]["reason"]

    if confidence < 0.40:
        log_low_confidence(raw_command, confidence)

    if should_fallback_to_general(confidence):
        intent = "general"

    enhanced_input = raw_command

    if should_use_agent(intent, confidence, AGENT_ROUTER):
        try:
            response = str(AGENT_ROUTER[intent](raw_command))
        except Exception as e:
            log_agent_error(intent, str(e))
            response = "Agent failed."
    else:
        response = generate_response(enhanced_input)

    store_and_learn(raw_command, response, intent)

    return intent, respond_in_language(response, language)


def process_command(command: str):
    raw_command = clean_user_input(command)

    if not raw_command:
        return "general", "Please type something."

    sub_commands = split_multi_intent(raw_command)

    if not should_treat_as_multi_command(sub_commands):
        return process_single_command(raw_command)

    results = []

    for sub_command in sub_commands:
        _, response = process_single_command(sub_command)
        results.append(response)

    return "multi_command", format_multi_response(results)


from brain.runtime_core import (  # noqa: E402
    process_command,
    process_command_detailed,
    process_single_command,
    process_single_command_detailed,
)
