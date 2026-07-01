import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# --- TOOL: a real function your agent can call ---
def get_ticket_details(ticket_id: str) -> str:
    """Returns details of a Jira ticket by ID."""
    
    # Fake ticket database for now
    tickets = {
        "PROJ-101": "Title: Login button broken on iOS. Priority: High. Assigned to: Ahmed.",
        "PROJ-102": "Title: Dashboard loads slowly. Priority: Medium. Assigned to: Sara.",
        "PROJ-103": "Title: Email notifications not sending. Priority: High. Assigned to: Unassigned.",
    }
    
    return tickets.get(ticket_id, f"Ticket {ticket_id} not found.")

def get_assignee_workload(assignee_name: str) -> str:
    """Returns how many tickets an assignee currently has."""
    workload = {
        "Ahmed": "3 open tickets",
        "Sara": "1 open ticket",
        "Unassigned": "0 tickets"
    }
    return workload.get(assignee_name, "Assignee not found.")

# --- Give the tool to the model ---
model = genai.GenerativeModel(
    model_name="gemini-3.5-flash",
    system_instruction="You are an engineering assistant. When asked about a ticket, use the get_ticket_details tool to look it up. Then analyze it and suggest next steps.",
    tools=[get_ticket_details, get_assignee_workload]  # <-- agent now has access to this function
)

chat = model.start_chat(enable_automatic_function_calling=True)

response = chat.send_message("Can you look up PROJ-101 and tell me if the assignee can handle it")
print(response.text)