import json
import os
import re
import datetime
from memory.vector_memory import store_memory


REMINDERS_FILE = "memory/reminders.json"


def load_reminders():
    if not os.path.exists(REMINDERS_FILE):
        return []

    try:
        with open(REMINDERS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        return []


def save_reminders(reminders):
    os.makedirs(os.path.dirname(REMINDERS_FILE), exist_ok=True)
    with open(REMINDERS_FILE, "w", encoding="utf-8") as f:
        json.dump(reminders, f, indent=4, ensure_ascii=False)


def get_next_reminder_id(reminders):
    if not reminders:
        return 1
    return max(r.get("id", 0) for r in reminders) + 1


def clean_value(value):
    if value is None:
        return None
    value = str(value).strip()
    return value if value else None


def add_reminder(text, time=None, date=None):
    try:
        reminders = load_reminders()

        reminder = {
            "id": get_next_reminder_id(reminders),
            "text": clean_value(text),
            "time": clean_value(time),
            "date": clean_value(date),
            "created": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "status": "active"
        }

        reminders.append(reminder)
        save_reminders(reminders)

        store_memory(
            f"Reminder set: {reminder['text']}",
            {
                "type": "reminder",
                "action": "add",
                "time": reminder["time"] or "",
                "date": reminder["date"] or ""
            }
        )

        return (
            "REMINDER SET\n\n"
            f"Reminder: {reminder['text']}\n"
            f"Time: {reminder['time'] or 'Not specified'}\n"
            f"Date: {reminder['date'] or 'Not specified'}\n"
            f"ID: {reminder['id']}\n\n"
            "Your reminder has been saved."
        )

    except Exception as e:
        return f"Reminder Agent error while adding reminder: {str(e)}"


def get_reminders(status="active"):
    try:
        reminders = load_reminders()

        if not reminders:
            return "No reminders set. Say remind me to followed by your reminder."

        if status:
            reminders = [r for r in reminders if r.get("status") == status]

        if not reminders:
            return f"No {status} reminders found."

        result = "YOUR REMINDERS\n\n"

        for reminder in reminders:
            result += (
                f"{reminder['id']}. {reminder['text']}\n"
                f"   Time: {reminder.get('time') or 'Not set'} | "
                f"Date: {reminder.get('date') or 'Not set'}\n"
                f"   Status: {reminder.get('status', 'active').upper()}\n\n"
            )

        return result.strip()

    except Exception as e:
        return f"Reminder Agent error while reading reminders: {str(e)}"


def delete_reminder(reminder_id):
    try:
        reminder_id = int(reminder_id)
        reminders = load_reminders()

        reminder_to_delete = next((r for r in reminders if r.get("id") == reminder_id), None)
        if not reminder_to_delete:
            return f"Reminder {reminder_id} not found."

        updated_reminders = [r for r in reminders if r.get("id") != reminder_id]
        save_reminders(updated_reminders)

        store_memory(
            f"Reminder deleted: {reminder_to_delete['text']}",
            {
                "type": "reminder",
                "action": "delete"
            }
        )

        return f"Reminder {reminder_id} deleted: {reminder_to_delete['text']}"

    except ValueError:
        return "Please provide a valid numeric reminder ID."
    except Exception as e:
        return f"Reminder Agent error while deleting reminder: {str(e)}"


def complete_reminder(reminder_id):
    try:
        reminder_id = int(reminder_id)
        reminders = load_reminders()

        for reminder in reminders:
            if reminder.get("id") == reminder_id:
                reminder["status"] = "completed"
                reminder["completed_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                save_reminders(reminders)

                store_memory(
                    f"Reminder completed: {reminder['text']}",
                    {
                        "type": "reminder",
                        "action": "complete"
                    }
                )

                return f"Reminder {reminder_id} marked as completed: {reminder['text']}"

        return f"Reminder {reminder_id} not found."

    except ValueError:
        return "Please provide a valid numeric reminder ID."
    except Exception as e:
        return f"Reminder Agent error while completing reminder: {str(e)}"


def find_due_reminders(current_date=None, current_time=None):
    try:
        reminders = load_reminders()
        due = []

        for reminder in reminders:
            if reminder.get("status") != "active":
                continue

            date_match = not current_date or reminder.get("date") == current_date
            time_match = not current_time or reminder.get("time") == current_time

            if date_match and time_match:
                due.append(reminder)

        return due

    except Exception:
        return []