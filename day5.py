import os
import json
import requests
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

# --- Tool 1: Get repository info ---
def get_repo_info(repo_name: str) -> str:
    """
    Gets basic information about a GitHub repository.
    repo_name should be in format: owner/repository (example: microsoft/vscode)
    """
    url = f"https://api.github.com/repos/{repo_name}"
    
    response = requests.get(url, headers=HEADERS)
    
    if response.status_code != 200:
        return f"Repository not found or error: {response.status_code}"
    
    data = response.json()
    
    # Extract only what the AI needs — don't send everything
    result = {
        "name": data["name"],
        "description": data["description"],
        "language": data["language"],
        "stars": data["stargazers_count"],
        "open_issues": data["open_issues_count"],
        "last_updated": data["updated_at"]
    }
    
    return json.dumps(result)

# --- Tool 2: Get open issues ---
def get_open_issues(repo_name: str) -> str:
    """
    Gets the latest open issues from a GitHub repository.
    repo_name should be in format: owner/repository (example: microsoft/vscode)
    """
    url = f"https://api.github.com/repos/{repo_name}/issues"
    
    # Only get 5 most recent open issues
    params = {
        "state": "open",
        "per_page": 5,
        "sort": "created",
        "direction": "desc"
    }
    
    response = requests.get(url, headers=HEADERS, params=params)
    
    if response.status_code != 200:
        return f"Could not fetch issues: {response.status_code}"
    
    issues = response.json()
    
    if not issues:
        return "No open issues found."
    
    # Extract only what matters
    result = []
    for issue in issues:
        result.append({
            "number": issue["number"],
            "title": issue["title"],
            "state": issue["state"],
            "created_at": issue["created_at"],
            "body": issue["body"][:200] if issue["body"] else "No description"
        })
    
    return json.dumps(result)


# --- Agent setup ---
model = genai.GenerativeModel(
    model_name="gemini-3.1-flash-lite",
    system_instruction="""You are a senior software engineering assistant.
You have access to GitHub repositories via tools.
When asked about a repository, fetch its info and issues.
Analyze the issues like a tech lead would — identify what type of problems they are,
which look most critical, and suggest what kind of developer should handle each one.""",
    tools=[get_repo_info, get_open_issues]
)

chat = model.start_chat(enable_automatic_function_calling=True)

print("GitHub Agent ready.\n")

while True:
    user_input = input("You: ")
    if user_input.lower() == "exit":
        break
    response = chat.send_message(user_input)
    print(f"\nAgent: {response.text}\n")