# server/services/openai_service.py
import os
from openai import OpenAI
from dotenv import load_dotenv

# .env laden (wie dotenv.config() in JS)
load_dotenv()

# OpenAI Client erstellen (identisch zu JS)
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

# 1:1 Portierung der chat(messages)-Funktion
async def chat(messages):
    """
    Entspricht exakt:
      export async function chat(messages) { ... }
    in openai.service.js
    """
    
    response = client.chat.completions.create(
        model="gpt-4.1-mini",   # identischer Modellname
        messages=messages,
        temperature=0.1
    )

    # JS: return response.choices[0].message;
    return response.choices[0].message
