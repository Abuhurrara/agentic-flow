import google.generativeai as genai
import requests
import json
import os
from dotenv import load_dotenv
from flask import Flask, request, jsonify

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

genai.configure(api_key=GEMINI_API_KEY)

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

# ─────────────────────────────────────────
# YOUR 3 TOOLS — same as before
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
        return "No files changed."
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
# NEW FUNCTION: Post review as GitHub comment
# ─────────────────────────────────────────
def post_github_comment(repo_name: str, pr_number: int, comment: str):
    """Posts the AI review as a real comment on the GitHub PR."""
    url = f"https://api.github.com/repos/{repo_name}/issues/{pr_number}/comments"

    body = f"## 🤖 AI PR Review\n\n{comment}\n\n---\n*Reviewed automatically by PR Review Agent*"

    response = requests.post(url, headers=HEADERS, json={"body": body})
    return response.status_code


# ─────────────────────────────────────────
# FLASK ROUTES
# ─────────────────────────────────────────
app = Flask(__name__)


@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "PR Review Agent is running"})


@app.route("/review", methods=["POST"])
def review():
    data = request.json
    repo = data.get("repo")
    pr_number = data.get("pr_number")

    if not repo or not pr_number:
        return jsonify({"error": "Please provide repo and pr_number"}), 400

    chat = model.start_chat(enable_automatic_function_calling=True)
    message = f"Review PR {pr_number} in {repo}"
    response = chat.send_message(message)

    return jsonify({
        "repo": repo,
        "pr_number": pr_number,
        "review": response.text
    })


# ─────────────────────────────────────────
# NEW ROUTE: GitHub calls this automatically
# ─────────────────────────────────────────
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json

    # GitHub sends many types of events
    # We only care about PR events
    if "pull_request" not in data:
        return jsonify({"status": "ignored — not a PR event"}), 200

    action = data.get("action")

    # Only review when PR is first opened or new commits pushed
    if action not in ["opened", "synchronize"]:
        return jsonify({"status": f"ignored — action was {action}"}), 200

    # Extract PR info from GitHub's payload
    pr_number = data["pull_request"]["number"]
    repo_name = data["repository"]["full_name"]
    pr_title = data["pull_request"]["title"]
    pr_author = data["pull_request"]["user"]["login"]

    print(f"\n🔔 New PR received: #{pr_number} — {pr_title} by {pr_author}")
    print(f"   Repo: {repo_name}")
    print(f"   Starting review...\n")

    # Run the agent
    chat = model.start_chat(enable_automatic_function_calling=True)
    message = f"Review PR {pr_number} in {repo_name}"
    response = chat.send_message(message)

    # Post review as a real GitHub comment
    status = post_github_comment(repo_name, pr_number, response.text)

    print(f"✅ Review posted. GitHub response: {status}\n")

    return jsonify({
        "status": "review completed",
        "pr": pr_number,
        "repo": repo_name,
        "comment_status": status
    })


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)