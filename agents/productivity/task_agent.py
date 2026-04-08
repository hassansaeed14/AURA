import json
import os
import datetime
from groq import Groq
from config.settings import GROQ_API_KEY, MODEL_NAME

client = Groq(api_key=GROQ_API_KEY)
TASKS_FILE = "memory/tasks.json"

def load_tasks():
    if not os.path.exists(TASKS_FILE):
        return []
    with open(TASKS_FILE, 'r') as f:
        return json.load(f)

def save_tasks(tasks):
    with open(TASKS_FILE, 'w') as f:
        json.dump(tasks, f, indent=4)

def add_task(task, priority="medium", due_date=None):
    tasks = load_tasks()
    new_task = {
        "id": len(tasks) + 1,
        "task": task,
        "priority": priority,
        "due_date": due_date,
        "status": "pending",
        "created": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    tasks.append(new_task)
    save_tasks(tasks)
    return (
        f"TASK ADDED\n\n"
        f"Task: {task}\n"
        f"Priority: {priority.upper()}\n"
        f"Due Date: {due_date or 'Not set'}\n"
        f"Status: Pending\n"
        f"Task ID: {new_task['id']}"
    )

def get_tasks(status=None):
    tasks = load_tasks()
    if not tasks:
        return "No tasks found. Add a task by saying 'add task [task name]'"

    if status:
        tasks = [t for t in tasks if t['status'] == status]

    result = "YOUR TASKS\n\n"
    pending = [t for t in tasks if t['status'] == 'pending']
    completed = [t for t in tasks if t['status'] == 'completed']

    if pending:
        result += "PENDING:\n"
        for task in pending:
            result += (
                f"{task['id']}. {task['task']}\n"
                f"   Priority: {task['priority'].upper()} | "
                f"Due: {task.get('due_date', 'Not set')}\n\n"
            )

    if completed:
        result += "COMPLETED:\n"
        for task in completed:
            result += f"{task['id']}. {task['task']} (Done)\n"

    return result

def complete_task(task_id):
    tasks = load_tasks()
    for task in tasks:
        if task['id'] == int(task_id):
            task['status'] = 'completed'
            task['completed_at'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            save_tasks(tasks)
            return f"Task {task_id} marked as completed: {task['task']}"
    return f"Task {task_id} not found."

def delete_task(task_id):
    tasks = load_tasks()
    tasks = [t for t in tasks if t['id'] != int(task_id)]
    save_tasks(tasks)
    return f"Task {task_id} deleted."

def plan_tasks(goal):
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are AURA Task Agent, an expert project manager. "
                    "Break down goals into actionable tasks. "
                    "Format:\n"
                    "TASK PLAN FOR: [goal]\n\n"
                    "PHASE 1: [Phase name]\n"
                    "Task 1: [Task]\n"
                    "Task 2: [Task]\n\n"
                    "PHASE 2: [Phase name]\n"
                    "Task 1: [Task]\n"
                    "Task 2: [Task]\n\n"
                    "TIMELINE:\n"
                    "[Suggested timeline]\n\n"
                    "PRIORITY ORDER:\n"
                    "1. [Most important first]\n"
                    "2. [Next]\n\n"
                    "SUCCESS METRICS:\n"
                    "[How to measure progress]"
                )
            },
            {"role": "user", "content": f"Create a task plan for: {goal}"}
        ],
        max_tokens=1000
    )
    return response.choices[0].message.content