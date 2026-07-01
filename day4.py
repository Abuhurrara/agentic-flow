import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# --- Load real data from file ---
# This runs ONCE when the program starts
# tickets_db is now a Python dictionary loaded from your file
with open("tickets.json", "r") as f:
    tickets_db = json.load(f)

# --- Tool 1: Get one specific ticket ---
def get_ticket_details(ticket_id: str) -> str:
    """Returns full details of a specific ticket by its ID."""
    ticket = tickets_db.get(ticket_id)
    if not ticket:
        return f"Ticket {ticket_id} not found."
    return json.dumps(ticket)

# --- Tool 2: List all tickets ---
def list_all_tickets() -> str:
    """Returns a list of all available tickets with their title and priority."""
    result = []
    for tid, data in tickets_db.items():
        result.append(f"{tid}: {data['title']} [{data['priority']}]")
    return "\n".join(result)

# --- Agent setup ---
model = genai.GenerativeModel(
    model_name="gemini-3.5-flash",
    system_instruction="""You are a project management assistant.
You have access to a live ticket database.
When asked, list tickets, look them up, and recommend which should be handled first based on priority and whether they are assigned or not.""",
    tools=[get_ticket_details, list_all_tickets]
)

chat = model.start_chat(enable_automatic_function_calling=True)

print("PM Agent ready. Ask about your tickets.\n")

while True:
    user_input = input("you: ")
    if user_input.lower() == "exit":
        break
    response = chat.send_message(user_input)
    print(f"\nAgent: {response.text}\n")