import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

model = genai.GenerativeModel(
    model_name="gemini-3.5-flash",
    system_instruction="You are a senior software engineer. When given a Jira ticket, you analyze it and suggest exactly what code changes need to be made. Be specific and technical."
)

ticket = """
Ticket ID: PROJ-101
Title: Login button not working on mobile
Description: Users on iOS Safari cannot tap the login button. It appears clickable but nothing happens.
Priority: High
"""

response = model.generate_content(f"Analyze this ticket and suggest what needs to be fixed:\n{ticket}")

print(response.text)