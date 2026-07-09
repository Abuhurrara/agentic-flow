import google.generativeai as genai
import json
import os
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# ─────────────────────────────────────────
# AGENT 1: ANALYST
# Job: Understand the ticket deeply
# ─────────────────────────────────────────
analyst = genai.GenerativeModel(
    model_name="gemini-3.1-flash-lite",
    system_instruction="""You are a senior technical analyst.
Your ONLY job is to analyze a ticket and output a structured analysis.

You must respond in this exact format:
PROBLEM TYPE: (Bug / Feature / Performance / Security)
SEVERITY: (Critical / High / Medium / Low)
ROOT CAUSE: (one sentence — what is most likely causing this)
SKILLS NEEDED: (what kind of developer should fix this)
KEY FILES: (which files/areas of the codebase are likely involved)
APPROACH: (2-3 sentences on the best technical approach to fix this)

Be precise. Be technical. No fluff."""
)

# ─────────────────────────────────────────
# AGENT 2: DEVELOPER
# Job: Write the actual code solution
# ─────────────────────────────────────────
developer = genai.GenerativeModel(
    model_name="gemini-3.1-flash-lite",
    system_instruction="""You are a senior software developer.
You receive a ticket AND a technical analysis from an analyst.
Your ONLY job is to write the actual code solution.

You must respond in this exact format:
SOLUTION SUMMARY: (one sentence — what you are doing)
CODE:
(write the actual code fix with comments explaining each part)
TESTING: (how to test this fix — specific steps)
EDGE CASES: (what edge cases does your solution handle)

Write real, working code. Not pseudocode. Not placeholders."""
)

# ─────────────────────────────────────────
# AGENT 3: REVIEWER
# Job: Review the developer's solution
# ─────────────────────────────────────────
reviewer = genai.GenerativeModel(
    model_name="gemini-3.1-flash-lite",
    system_instruction="""You are a principal engineer doing a code review.
You receive a ticket, an analysis, and a developer's solution.
Your ONLY job is to review the solution critically.

You must respond in this exact format:
QUALITY SCORE: (1-10)
BUGS FOUND: (list any bugs or logic errors, or say "None found")
SECURITY ISSUES: (list any security concerns, or say "None found")
IMPROVEMENTS: (list specific improvements with better code examples)
VERDICT: (APPROVE / REQUEST CHANGES / REJECT)
REASON: (one sentence explaining your verdict)"""
)


# ─────────────────────────────────────────
# THE PIPELINE — agents talking to each other
# ─────────────────────────────────────────
def run_pipeline(ticket: str):
    print("\n" + "="*60)
    print("🎫 TICKET RECEIVED")
    print("="*60)
    print(ticket)

    # ── STEP 1: Analyst reads the ticket ──
    print("\n" + "─"*60)
    print("🔍 AGENT 1: ANALYST is working...")
    print("─"*60)

    analyst_chat = analyst.start_chat()
    analyst_response = analyst_chat.send_message(
        f"Analyze this ticket:\n\n{ticket}"
    )
    analysis = analyst_response.text
    print(analysis)

    # ── STEP 2: Developer reads ticket + analysis ──
    print("\n" + "─"*60)
    print("💻 AGENT 2: DEVELOPER is working...")
    print("─"*60)

    developer_chat = developer.start_chat()
    developer_response = developer_chat.send_message(
        f"""Here is the ticket:
{ticket}

Here is the analyst's findings:
{analysis}

Now write the code solution."""
    )
    solution = developer_response.text
    print(solution)

    # ── STEP 3: Reviewer reads everything ──
    print("\n" + "─"*60)
    print("🔎 AGENT 3: REVIEWER is working...")
    print("─"*60)

    reviewer_chat = reviewer.start_chat()
    reviewer_response = reviewer_chat.send_message(
        f"""Here is the original ticket:
{ticket}

Here is the analyst's findings:
{analysis}

Here is the developer's solution:
{solution}

Now review the solution."""
    )
    review = reviewer_response.text
    print(review)

    # ── FINAL REPORT ──
    print("\n" + "="*60)
    print("📋 FINAL PIPELINE REPORT")
    print("="*60)
    print(f"\n📌 TICKET:\n{ticket}")
    print(f"\n🔍 ANALYSIS:\n{analysis}")
    print(f"\n💻 SOLUTION:\n{solution}")
    print(f"\n🔎 REVIEW:\n{review}")
    print("\n" + "="*60)

    return {
        "ticket": ticket,
        "analysis": analysis,
        "solution": solution,
        "review": review
    }


# ─────────────────────────────────────────
# RUN IT
# ─────────────────────────────────────────
if __name__ == "__main__":
    # Test ticket 1 — a real bug
    ticket_1 = """
    Ticket ID: PROJ-201
    Title: User passwords stored in plain text in database
    Priority: Critical
    Description: During a security audit we discovered that user passwords
    are being stored as plain text in the users table. This is a critical
    security vulnerability. We need to immediately hash all existing passwords
    and update the registration and login flow to use proper hashing.
    Tech Stack: Python, Flask, PostgreSQL
    """

    run_pipeline(ticket_1)