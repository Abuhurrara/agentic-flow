import google.generativeai as genai
import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
CLICKUP_TOKEN = os.getenv("CLICKUP_TOKEN")

HEADERS = {
    "Authorization": CLICKUP_TOKEN,
    "Content-Type": "application/json"
}


# ─────────────────────────────────────────
# TOOL 1: Get all tasks from a ClickUp list
# ─────────────────────────────────────────
def get_clickup_tasks(list_id: str) -> str:
    """
    Fetches all tasks from a ClickUp list.
    list_id: the ID of the ClickUp list (found in the URL)
    """
    url = f"https://api.clickup.com/api/v2/list/{list_id}/task"

    params = {
        "archived": "false",
        "include_closed": "false"
    }

    response = requests.get(url, headers=HEADERS, params=params)

    if response.status_code != 200:
        return f"Could not fetch tasks: {response.status_code} — {response.text}"

    data = response.json()
    tasks = data.get("tasks", [])

    if not tasks:
        return "No tasks found in this list."

    result = []
    for task in tasks:
        result.append({
            "id": task["id"],
            "name": task["name"],
            "description": (task.get("description") or "No description")[:300],
            "status": task["status"]["status"],
            "priority": task["priority"]["priority"] if task.get("priority") else "None",
            "assignees": [a["username"] for a in task.get("assignees", [])],
            "due_date": task.get("due_date")
        })

    return json.dumps(result)


# ─────────────────────────────────────────
# TOOL 2: Get details of one specific task
# ─────────────────────────────────────────
def get_clickup_task_details(task_id: str) -> str:
    """
    Gets full details of a specific ClickUp task including comments.
    task_id: the ID of the ClickUp task
    """
    url = f"https://api.clickup.com/api/v2/task/{task_id}"
    response = requests.get(url, headers=HEADERS)

    if response.status_code != 200:
        return f"Could not fetch task: {response.status_code}"

    task = response.json()

    result = {
        "id": task["id"],
        "name": task["name"],
        "description": task.get("description") or "No description",
        "status": task["status"]["status"],
        "priority": task["priority"]["priority"] if task.get("priority") else "None",
        "assignees": [a["username"] for a in task.get("assignees", [])],
        "tags": [t["name"] for t in task.get("tags", [])],
        "due_date": task.get("due_date")
    }

    return json.dumps(result)


# ─────────────────────────────────────────
# THE AGENT
# ─────────────────────────────────────────
model = genai.GenerativeModel(
    model_name="gemini-3.1-flash-lite",
    system_instruction="""You are a senior project manager.

You have access to a ClickUp list. When asked to review tasks:

1. Fetch all tasks in the list
2. Analyze each one by:
   - Status (To Do / In Progress / On Dev / Done etc.)
   - Priority (Urgent / High / Normal / Low / None set)
   - Whether it's assigned or unassigned
   - Whether it has a due date

3. Give a clear, practical breakdown:

## Task Overview
(how many tasks total, how many unassigned, how many overdue or no due date)

## Needs Immediate Attention
(unassigned + high priority tasks, or tasks with no priority set that look urgent based on description)

## On Track
(tasks that are assigned, prioritized, and moving)

## Recommendations
(what the team should do next, any process gaps you notice like missing priorities or assignees)

Be direct and practical, like a PM giving a real Monday morning update.""",
    tools=[get_clickup_tasks, get_clickup_task_details]
)


# ─────────────────────────────────────────
# RUN IT
# ─────────────────────────────────────────
if __name__ == "__main__":
    chat = model.start_chat(enable_automatic_function_calling=True)

    print("="*60)
    print("   ClickUp Task Reviewer")
    print("="*60)
    print("\nExample: 'Review the tasks in list 901234567890'\n")

    while True:
        user_input = input("You: ")
        if user_input.lower() == "exit":
            break
        response = chat.send_message(user_input)
        print(f"\nAgent:\n{response.text}\n")
        print("─"*60 + "\n")