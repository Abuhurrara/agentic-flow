import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

model = genai.GenerativeModel(
    model_name="gemini-3.5-flash",
    system_instruction="You are a senior software engineer. You help analyze Jira tickets and suggest code fixes. Be specific and technical."
)

# This starts a chat session — it remembers everything said
chat = model.start_chat(history=[])

print("Agent ready. Type your message. Type 'exit' to quit.\n")

while True:
    user_input = input("You: ")
    
    if user_input.lower() == "exit":
        print("Session ended.")
        break

    response = chat.send_message(user_input)
    print(f"\nAgent: {response.text}\n")