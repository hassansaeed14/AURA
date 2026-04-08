import math
import re
from groq import Groq
from config.settings import GROQ_API_KEY, MODEL_NAME

client = Groq(api_key=GROQ_API_KEY)

def solve_math(problem):
    print(f"\nAURA Math Agent: {problem}")

    # Try direct calculation first
    try:
        # Clean the expression
        expr = problem.lower()
        expr = expr.replace('x', '*').replace('×', '*').replace('÷', '/')
        expr = expr.replace('squared', '**2').replace('cubed', '**3')
        expr = expr.replace('sqrt', 'math.sqrt').replace('pi', str(math.pi))

        # Extract pure math expression
        math_expr = re.sub(r'[^0-9+\-*/().math sqrte]', '', expr)

        if math_expr and any(c.isdigit() for c in math_expr):
            result = eval(math_expr, {"math": math, "__builtins__": {}})
            return f"Math Solution\n\nProblem: {problem}\nAnswer: {result}\n\nCalculated directly."

    except:
        pass

    # Use AI for complex problems
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are AURA Math Agent, an expert mathematician. "
                    "Solve math problems step by step. "
                    "Show all working and explain each step clearly. "
                    "Format:\n"
                    "PROBLEM: [restate problem]\n"
                    "SOLUTION:\n"
                    "Step 1: [first step]\n"
                    "Step 2: [second step]\n"
                    "ANSWER: [final answer]\n"
                    "EXPLANATION: [brief explanation]\n"
                    "No markdown symbols."
                )
            },
            {
                "role": "user",
                "content": f"Solve this math problem: {problem}"
            }
        ],
        max_tokens=1000
    )
    return response.choices[0].message.content