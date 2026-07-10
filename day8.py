import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# ─────────────────────────────────────────
# AGENT 1: ANALYST — same as Day 7
# ─────────────────────────────────────────
analyst = genai.GenerativeModel(
    model_name="gemini-3.1-flash-lite",
    system_instruction="""You are a senior technical analyst.
Your ONLY job is to analyze a ticket and output a structured analysis.

Respond in this exact format:
PROBLEM TYPE: (Bug / Feature / Performance / Security)
SEVERITY: (Critical / High / Medium / Low)
ROOT CAUSE: (one sentence)
SKILLS NEEDED: (what kind of developer)
KEY FILES: (which files are likely involved)
APPROACH: (2-3 sentences on best technical approach)"""
)

# ─────────────────────────────────────────
# AGENT 2: DEVELOPER — now accepts feedback
# ─────────────────────────────────────────
developer = genai.GenerativeModel(
    model_name="gemini-3.1-flash-lite",
    system_instruction="""You are a senior software developer.
You receive a ticket, an analysis, and sometimes reviewer feedback.
Your job is to write or improve the code solution based on all inputs.

Respond in this exact format:
SOLUTION SUMMARY: (one sentence)
CHANGES MADE: (if this is a revision, list what you changed and why)
CODE:
(write the actual working code with comments)
TESTING: (specific test steps)
EDGE CASES: (what edge cases you handle)"""
)

# ─────────────────────────────────────────
# AGENT 3: REVIEWER — gives structured verdict
# ─────────────────────────────────────────
reviewer = genai.GenerativeModel(
    model_name="gemini-3.1-flash-lite",
    system_instruction="""You are a principal engineer doing a code review.
You review the developer's solution critically and honestly.

Respond in this exact format:
QUALITY SCORE: (1-10)
BUGS FOUND: (list bugs or say "None found")
SECURITY ISSUES: (list issues or say "None found")
IMPROVEMENTS: (list specific improvements with better code, or say "None needed")
VERDICT: (APPROVE or REQUEST CHANGES — nothing else)
REASON: (one sentence)"""
)


# ─────────────────────────────────────────
# THE ITERATIVE PIPELINE
# ─────────────────────────────────────────
def run_iterative_pipeline(ticket: str, max_rounds: int = 3):
    print("\n" + "="*60)
    print("🎫 TICKET RECEIVED")
    print("="*60)
    print(ticket)

    # ── Step 1: Analyst runs once ──
    print("\n" + "─"*60)
    print("🔍 AGENT 1: ANALYST")
    print("─"*60)
    analyst_chat = analyst.start_chat()
    analysis = analyst_chat.send_message(
        f"Analyze this ticket:\n\n{ticket}"
    ).text
    print(analysis)

    # ── Step 2: Developer + Reviewer loop ──
    feedback = None          # no feedback on first round
    solution = None
    round_number = 0

    while round_number < max_rounds:
        round_number += 1
        print(f"\n{'─'*60}")
        print(f"🔄 ROUND {round_number}")
        print(f"{'─'*60}")

        # Developer writes or revises solution
        print(f"\n💻 DEVELOPER (Round {round_number})")

        if feedback is None:
            # First round — no feedback yet
            dev_message = f"""Ticket:
{ticket}

Analyst findings:
{analysis}

Write the code solution."""
        else:
            # Later rounds — include reviewer feedback
            dev_message = f"""Ticket:
{ticket}

Analyst findings:
{analysis}

Your previous solution:
{solution}

Reviewer feedback that you MUST address:
{feedback}

Revise your solution to fix all the issues raised."""

        developer_chat = developer.start_chat()
        solution = developer_chat.send_message(dev_message).text
        print(solution)

        # Reviewer checks the solution
        print(f"\n🔎 REVIEWER (Round {round_number})")

        review_message = f"""Ticket:
{ticket}

Analyst findings:
{analysis}

Developer solution (Round {round_number}):
{solution}

Review this solution critically."""

        reviewer_chat = reviewer.start_chat()
        review = reviewer_chat.send_message(review_message).text
        print(review)

        # Check verdict
        if "VERDICT: APPROVE" in review:
            print(f"\n✅ APPROVED after {round_number} round(s)!")
            break
        else:
            print(f"\n🔁 Reviewer requested changes. Starting Round {round_number + 1}...")
            feedback = review  # pass feedback to developer next round

        if round_number == max_rounds:
            print(f"\n⚠️  Max rounds ({max_rounds}) reached. Escalating to human review.")

    # ── Final Report ──
    print("\n" + "="*60)
    print("📋 FINAL REPORT")
    print("="*60)
    print(f"Rounds needed: {round_number}")
    print(f"\n🔍 ANALYSIS:\n{analysis}")
    print(f"\n💻 FINAL SOLUTION:\n{solution}")
    print(f"\n🔎 FINAL REVIEW:\n{review}")


# ─────────────────────────────────────────
# RUN IT
# ─────────────────────────────────────────
if __name__ == "__main__":
    ticket = """
    Ticket ID: PROJ-202
    Title: API endpoint returns all user data including passwords
    Priority: Critical
    Description: The /api/users endpoint currently returns the full user
    object from the database including hashed passwords, email addresses,
    and internal IDs. This data should never be exposed publicly.
    Any authenticated user can call this endpoint and see other users data.
    Tech Stack: Python, Flask, PostgreSQL
    """

    run_iterative_pipeline(ticket, max_rounds=3)