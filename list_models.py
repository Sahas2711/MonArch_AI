import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
api_key = os.getenv("GROQ_API_KEY")
client = Groq(api_key=api_key)

try:
    models = client.models.list()
    active_chat_models = [m.id for m in models.data if "whisper" not in m.id]
    print("\n--- Available Groq Chat Models for your API Key ---")
    for m_id in sorted(active_chat_models):
        print(f"  {m_id}")
    print("---------------------------------------------------\n")
except Exception as e:
    print("Error fetching models from Groq:", e)
