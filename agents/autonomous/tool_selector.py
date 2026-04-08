def choose_tool(task):

    task = task.lower()

    if "code" in task or "program" in task:
        return "coding_agent"

    if "search" in task or "research" in task:
        return "web_agent"

    if "file" in task or "save" in task:
        return "file_agent"

    if "fix" in task or "debug" in task:
        return "debug_agent"

    return "general_agent"