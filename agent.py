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
# YOUR 3 TOOLS — same as Day 7
# ─────────────────────────────────────────
def get_pr_details(repo_name: str, pr_number: int) -> str:
    """Gets the details of a Pull Request including title, description and author.
    repo_name format: owner/repository
    pr_number: the PR number
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


def get_pr_files(repo_name: str, pr_number: int) -> str:
    """Gets the actual code changes of a Pull Request.
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
    for file in files[:5]:
        result.append({
            "filename": file["filename"],
            "status": file["status"],
            "additions": file["additions"],
            "deletions": file["deletions"],
            "patch": file.get("patch", "Binary file")[:800]
        })
    return json.dumps(result)


def get_pr_comments(repo_name: str, pr_number: int) -> str:
    """Gets existing review comments on a Pull Request.
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
# AGENT
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
With a one line reason.""",
    tools=[get_pr_details, get_pr_files, get_pr_comments]
)


# ─────────────────────────────────────────
# FLASK WEB SERVER — this is what's new
# ─────────────────────────────────────────
app = Flask(__name__)

@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "PR Review Agent is running"})


@app.route("/review", methods=["POST"])
def review():
    # Read the incoming request
    data = request.json
    repo = data.get("repo")
    pr_number = data.get("pr_number")

    if not repo or not pr_number:
        return jsonify({"error": "Please provide repo and pr_number"}), 400

    # Start a fresh chat for each review
    chat = model.start_chat(enable_automatic_function_calling=True)

    # Ask the agent to review
    message = f"Review PR {pr_number} in {repo}"
    response = chat.send_message(message)

    return jsonify({
        "repo": repo,
        "pr_number": pr_number,
        "review": response.text
    })


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)