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
def get_my_tasks(list_id: str, my_username: str) -> str:
    """
    Fetches only tasks assigned to a specific person from a ClickUp list,
    grouped by their status.
    list_id: the ID of the ClickUp list
    my_username: the username to filter by (only their tasks are returned)
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

    # ── FILTER: only keep tasks assigned to my_username ──
    my_tasks = []
    for task in tasks:
        assignee_names = [a["username"] for a in task.get("assignees", [])]

        # Only keep this task if my_username is one of the assignees
        if my_username in assignee_names:
            my_tasks.append({
                "id": task["id"],
                "name": task["name"],
                "description": (task.get("description") or "No description")[:200],
                "status": task["status"]["status"],
                "priority": task["priority"]["priority"] if task.get("priority") else "None",
                "due_date": task.get("due_date")
            })

    if not my_tasks:
        return f"No tasks assigned to {my_username} in this list."

    # ── GROUP: organize tasks by their status ──
    grouped = {}
    for task in my_tasks:
        status = task["status"]
        if status not in grouped:
            grouped[status] = []
        grouped[status].append(task)

    result = {
        "total_my_tasks": len(my_tasks),
        "grouped_by_status": grouped
    }

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
    system_instruction="""You are a personal standup assistant for a developer named Harris.

You fetch ONLY Harris's tickets, already grouped by status.

Give a report in this EXACT format:

## 🌅 Standup Summary
(2-3 sentences: how many tickets Harris has total, what he's actively working on right now, what's most urgent)

## 📋 My Tickets by Status

### 🔵 In Progress
(list each ticket: name + priority + one line on what it is)

### 🟢 On Dev / Testing
(same format)

### ⚪ To Do
(same format)

### ✅ Done / Ready for Deployment
(same format)

(Only show status sections that actually have tickets. Skip empty ones.)

## ⚡ Suggested Focus Today
(based on priority and status, what should Harris focus on today? Pick 1-2 specific tickets and say why)

Be concise and practical. This is a daily standup tool, not a lengthy report.""",
    tools=[get_my_tasks]
)


# ─────────────────────────────────────────
# RUN IT
# ─────────────────────────────────────────
if __name__ == "__main__":
    chat = model.start_chat(enable_automatic_function_calling=True)

    MY_USERNAME = "Harris"   # ← your ClickUp username
    MY_LIST_ID = "901710637280"  # ← your list ID

    print("="*60)
    print(f"   Standup Assistant for {MY_USERNAME}")
    print("="*60)
    print()

    while True:
        user_input = input("You (or press Enter for standup): ")

        if user_input.lower() == "exit":
            break

        # If they just press Enter, run the default standup
        if user_input.strip() == "":
            user_input = f"Give me my standup for list {MY_LIST_ID}, my username is {MY_USERNAME}"

        response = chat.send_message(user_input)
        print(f"\nAgent:\n{response.text}\n")
        print("─"*60 + "\n")