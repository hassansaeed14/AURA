from groq import Groq
from config.settings import GROQ_API_KEY, MODEL_NAME

client = Groq(api_key=GROQ_API_KEY)

def generate_quiz(topic, num_questions=5, difficulty="medium"):
    print(f"\nAURA Quiz Agent: {topic}")

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": (
                    f"You are AURA Quiz Agent, an expert educator. "
                    f"Generate a {difficulty} difficulty quiz. "
                    f"Format:\n"
                    f"QUIZ: {topic}\n"
                    f"Difficulty: {difficulty.upper()}\n\n"
                    f"Question 1:\n"
                    f"[Question text]\n"
                    f"A) [Option]\n"
                    f"B) [Option]\n"
                    f"C) [Option]\n"
                    f"D) [Option]\n"
                    f"Correct Answer: [Letter]\n"
                    f"Explanation: [Why this is correct]\n\n"
                    f"[Repeat for all questions]\n\n"
                    f"QUIZ SUMMARY:\n"
                    f"Total Questions: {num_questions}\n"
                    f"Topic: {topic}\n"
                    f"Good luck!"
                )
            },
            {
                "role": "user",
                "content": f"Generate {num_questions} {difficulty} quiz questions about: {topic}"
            }
        ],
        max_tokens=2000
    )
    return response.choices[0].message.content

def check_answer(question, user_answer, correct_answer):
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are AURA Quiz Agent. "
                    "Check if the answer is correct and explain. "
                    "Format:\n"
                    "ANSWER CHECK\n\n"
                    "Your Answer: [user answer]\n"
                    "Correct Answer: [correct answer]\n"
                    "Result: CORRECT / INCORRECT\n\n"
                    "EXPLANATION:\n[Detailed explanation of the correct answer]"
                )
            },
            {
                "role": "user",
                "content": f"Question: {question}\nUser answered: {user_answer}\nCorrect answer: {correct_answer}"
            }
        ],
        max_tokens=400
    )
    return response.choices[0].message.content

def generate_flashcards(topic, num_cards=10):
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are AURA Quiz Agent. "
                    f"Generate {num_cards} flashcards for studying. "
                    "Format each card as:\n"
                    "CARD [N]:\n"
                    "FRONT: [Question or term]\n"
                    "BACK: [Answer or definition]\n\n"
                    "Make them educational and clear."
                )
            },
            {"role": "user", "content": f"Generate flashcards for: {topic}"}
        ],
        max_tokens=1500
    )
    return response.choices[0].message.content