from agents.autonomous.tool_selector import choose_tool
from agents.autonomous.coding_agent import write_code
from agents.autonomous.debug_agent import fix_code


def execute_plan(plan):

    steps = plan.split("\n")

    results = []

    for step in steps:

        tool = choose_tool(step)

        if tool == "coding_agent":
            result = write_code(step)

        elif tool == "debug_agent":
            result = fix_code(step)

        else:
            result = f"Executed step: {step}"

        results.append(result)

    return results