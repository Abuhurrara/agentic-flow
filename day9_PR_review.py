import google.generativeai as genai
import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

# ─────────────────────────────────────────
# TOOL 1: Fetch open issues from any repo
# ─────────────────────────────────────────
def get_open_issues(repo_name: str, limit: int = 10) -> str:
    """
    Fetches open issues from a GitHub repository.
    repo_name format: owner/repository (example: facebook/react)
    limit: how many issues to fetch (default 10, max 20)
    """
    url = f"https://api.github.com/repos/{repo_name}/issues"

    params = {
        "state": "open",
        "per_page": min(limit, 20),
        "sort": "created",
        "direction": "desc"
    }

    response = requests.get(url, headers=HEADERS, params=params)

    if response.status_code != 200:
        return f"Could not fetch issues: {response.status_code}"

    issues = response.json()

    if not issues:
        return "No open issues found."

    result = []
    for issue in issues:
        # Skip pull requests — GitHub API returns them as issues too
        if "pull_request" in issue:
            continue

        result.append({
            "number": issue["number"],
            "title": issue["title"],
            "body": issue["body"][:300] if issue["body"] else "No description",
            "labels": [l["name"] for l in issue["labels"]],
            "created_at": issue["created_at"],
            "comments": issue["comments"]
        })

    return json.dumps(result)


# ─────────────────────────────────────────
# TOOL 2: Get details of one specific issue
# ─────────────────────────────────────────
def get_issue_details(repo_name: str, issue_number: int) -> str:
    """
    Gets full details of a specific GitHub issue including all comments.
    repo_name format: owner/repository
    issue_number: the issue number
    """
    # Get issue details
    url = f"https://api.github.com/repos/{repo_name}/issues/{issue_number}"
    response = requests.get(url, headers=HEADERS)

    if response.status_code != 200:
        return f"Could not fetch issue: {response.status_code}"

    issue = response.json()

    # Get comments on the issue
    comments_url = f"https://api.github.com/repos/{repo_name}/issues/{issue_number}/comments"
    comments_response = requests.get(comments_url, headers=HEADERS)
    comments = comments_response.json() if comments_response.status_code == 200 else []

    result = {
        "number": issue["number"],
        "title": issue["title"],
        "body": issue["body"][:500] if issue["body"] else "No description",
        "labels": [l["name"] for l in issue["labels"]],
        "state": issue["state"],
        "created_at": issue["created_at"],
        "comments_count": issue["comments"],
        "recent_comments": [
            {
                "author": c["user"]["login"],
                "body": c["body"][:200]
            }
            for c in comments[:3]  # only last 3 comments
        ]
    }

    return json.dumps(result)


# ─────────────────────────────────────────
# TOOL 3: Get repo stats for context
# ─────────────────────────────────────────
def get_repo_stats(repo_name: str) -> str:
    """
    Gets overall repository statistics to understand project health.
    repo_name format: owner/repository
    """
    url = f"https://api.github.com/repos/{repo_name}"
    response = requests.get(url, headers=HEADERS)

    if response.status_code != 200:
        return f"Could not fetch repo: {response.status_code}"

    data = response.json()

    result = {
        "name": data["name"],
        "description": data["description"],
        "language": data["language"],
        "open_issues_count": data["open_issues_count"],
        "stars": data["stargazers_count"],
        "forks": data["forks_count"],
        "last_updated": data["updated_at"],
        "default_branch": data["default_branch"]
    }

    return json.dumps(result)


# ─────────────────────────────────────────
# THE AGENT
# ─────────────────────────────────────────
model = genai.GenerativeModel(
    model_name="gemini-3.1-flash-lite",
    system_instruction="""You are a senior engineering manager and sprint planner.

You have access to GitHub repositories. When asked to create a work plan:

1. First get the repo stats to understand the project
2. Then fetch open issues to see what needs doing
3. Analyze and categorize every issue by:
   - Type: Bug / Feature / Improvement / Documentation / Security
   - Priority: Critical / High / Medium / Low
   - Effort: Small (1-2 days) / Medium (3-5 days) / Large (1-2 weeks)

4. Output a structured sprint plan in this format:

## Repository Overview
(brief summary of the project and its health)

## Issue Analysis
(table of all issues with Type, Priority, Effort columns)

## Recommended Sprint Plan

### 🔴 Do First (Critical/High Priority)
(list issues with effort estimates and why they're urgent)

### 🟡 Do Next (Medium Priority)
(list issues with effort estimates)

### 🟢 Do Later (Low Priority / Nice to have)
(list issues with effort estimates)

## Team Recommendation
(what kind of developers are needed, how many, estimated total sprint duration)

## Risk Assessment
(what could go wrong, dependencies between issues, blockers)

Be specific, practical, and actionable. A real team should be able to pick this up and start working.""",
    tools=[get_repo_stats, get_open_issues, get_issue_details]
)


# ─────────────────────────────────────────
# RUN IT
# ─────────────────────────────────────────
if __name__ == "__main__":
    chat = model.start_chat(enable_automatic_function_calling=True)

    print("="*60)
    print("   GitHub Issues Sprint Planner")
    print("="*60)
    print("\nExamples:")
    print("  'Create a work plan for facebook/react'")
    print("  'What are the critical issues in torvalds/linux'")
    print("  'Plan a sprint for my-username/my-repo'")
    print()

    while True:
        user_input = input("You: ")
        if user_input.lower() == "exit":
            break
        response = chat.send_message(user_input)
        print(f"\nAgent:\n{response.text}\n")
        print("─"*60 + "\n")