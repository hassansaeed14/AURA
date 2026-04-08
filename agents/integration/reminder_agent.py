import json
import os
import datetime
from groq import Groq
from config.settings import GROQ_API_KEY, MODEL_NAME

client = Groq(api_key=GROQ_API_KEY)
REMINDERS_FILE = "memory/reminders.json"

def load_reminders():
    if not os.path.exists(REMINDERS_FILE):
        return []
    with open(REMINDERS_FILE, 'r') as f:
        return json.load(f)

def save_reminders(reminders):
    with open(REMINDERS_FILE, 'w') as f:
        json.dump(reminders, f, indent=4)

def add_reminder(text, time=None, date=None):
    reminders = load_reminders()
    reminder = {
        "id": len(reminders) + 1,
        "text": text,
        "time": time,
        "date": date,
        "created": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "status": "active"
    }
    reminders.append(reminder)
    save_reminders(reminders)
    return (
        f"REMINDER SET\n\n"
        f"Reminder: {text}\n"
        f"Time: {time or 'Not specified'}\n"
        f"Date: {date or 'Not specified'}\n"
        f"ID: {reminder['id']}\n\n"
        f"I will remind you about this!"
    )

def get_reminders():
    reminders = load_reminders()
    if not reminders:
        return "No reminders set. Say 'remind me to [task]' to add one."

    active = [r for r in reminders if r['status'] == 'active']
    result = "YOUR REMINDERS\n\n"

    if active:
        for r in active:
            result += (
                f"{r['id']}. {r['text']}\n"
                f"   Time: {r.get('time', 'Not set')} | "
                f"Date: {r.get('date', 'Not set')}\n\n"
            )
    else:
        result += "No active reminders."

    return result

def delete_reminder(reminder_id):
    reminders = load_reminders()
    reminders = [r for r in reminders if r['id'] != int(reminder_id)]
    save_reminders(reminders)
    return f"Reminder {reminder_id} deleted."