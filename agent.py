import google.generativeai as genai
import requests
import json
import os
from dotenv import load_dotenv
from flask import Flask, request, jsonify

# Load secrets from .env file
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

genai.configure(api_key=GEMINI_API_KEY)

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

# ─────────────────────────────────────────
# TOOL 1: Get PR details
# ─────────────────────────────────────────
def get_pr_details(repo_name: str, pr_number: int) -> str:
    """
    Gets the details of a Pull Request including title, description, and author.
    repo_name format: owner/repository (example: facebook/react)
    pr_number: the number of the PR (example: 36881)
    """
    url = f"https://api.github.com/repos/{repo_name}/pulls/{pr_number}"
    response = requests.get(url, headers=HEADERS)

    if response.status_code != 200:
        return f"Could not fetch PR: {response.status_code}"

    data = response.json()

    result = {
        "title": data["title"],
        "author": data["user"]["login"],
        "state": data["state"],
        "description": data["body"][:500] if data["body"] else "No description",
        "changed_files": data["changed_files"],
        "additions": data["additions"],
        "deletions": data["deletions"],
        "base_branch": data["base"]["ref"],
        "head_branch": data["head"]["ref"]
    }

    return json.dumps(result)


# ─────────────────────────────────────────
# TOOL 2: Get the actual code changes
# ─────────────────────────────────────────
def get_pr_files(repo_name: str, pr_number: int) -> str:
    """
    Gets the actual code changes (diff) of a Pull Request.
    Returns each changed file with what was added and removed.
    repo_name format: owner/repository
    pr_number: the PR number
    """
    url = f"https://api.github.com/repos/{repo_name}/pulls/{pr_number}/files"
    response = requests.get(url, headers=HEADERS)

    if response.status_code != 200:
        return f"Could not fetch PR files: {response.status_code}"

    files = response.json()

    if not files:
        return "No files changed in this PR."

    result = []
    for file in files[:5]:  # limit to 5 files so AI doesn't get overwhelmed
        result.append({
            "filename": file["filename"],
            "status": file["status"],        # added, modified, removed
            "additions": file["additions"],
            "deletions": file["deletions"],
            "patch": file.get("patch", "Binary file or too large to display")[:800]
        })

    return json.dumps(result)


# ─────────────────────────────────────────
# TOOL 3: Get existing PR comments
# ─────────────────────────────────────────
def get_pr_comments(repo_name: str, pr_number: int) -> str:
    """
    Gets existing review comments on a Pull Request.
    Useful to see what has already been flagged before adding new review.
    repo_name format: owner/repository
    pr_number: the PR number
    """
    url = f"https://api.github.com/repos/{repo_name}/pulls/{pr_number}/comments"
    response = requests.get(url, headers=HEADERS)

    if response.status_code != 200:
        return f"Could not fetch comments: {response.status_code}"

    comments = response.json()

    if not comments:
        return "No existing review comments."

    result = []
    for comment in comments[:5]:
        result.append({
            "author": comment["user"]["login"],
            "file": comment["path"],
            "comment": comment["body"][:300]
        })

    return json.dumps(result)


# ─────────────────────────────────────────
# AGENT SETUP
# ─────────────────────────────────────────
model = genai.GenerativeModel(
    model_name="gemini-2.5-flash",
    system_instruction="""You are a senior software engineer conducting a professional PR review.

When given a PR to review:
1. First fetch the PR details to understand what it's trying to do
2. Then fetch the actual code changes to review the implementation
3. Then check existing comments so you don't repeat what's already been said
4. Give a structured review with these sections:

## Summary
What this PR does in simple terms.

## Code Quality
Is the code clean, readable, well structured?

## Potential Bugs
Any logic errors, edge cases not handled, or things that could break?

## Security Concerns
Any hardcoded secrets, SQL injection risks, or unsafe operations?

## Suggestions
Specific improvements with example code where possible.

## Verdict
One of: APPROVE / REQUEST CHANGES / NEEDS DISCUSSION
With a one line reason.

Be direct, specific, and technical. Reference actual line changes when possible.""",
    tools=[get_pr_details, get_pr_files, get_pr_comments]
)

chat = model.start_chat(enable_automatic_function_calling=True)

print("=" * 50)
print("   PR Review Agent — Ready")
print("=" * 50)
print("\nExample: 'Review PR 36881 in facebook/react'\n")

while True:
    user_input = input("You: ")
    if user_input.lower() == "exit":
        break
    response = chat.send_message(user_input)
    print(f"\nAgent:\n{response.text}\n")
    print("-" * 50 + "\n")