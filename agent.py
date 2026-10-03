"""
Two-way WhatsApp AI bot (Agno + FastAPI + Groq Qwen)
Deployed on Render.com - runs 24/7 in the cloud.
"""

import os
import requests
from fastapi import FastAPI, Request, Query, BackgroundTasks
from fastapi.responses import PlainTextResponse
from dotenv import load_dotenv
from agno.agent import Agent
from agno.models.groq import Groq

load_dotenv()

app = FastAPI()

ACCESS_TOKEN = os.environ.get("WHATSAPP_ACCESS_TOKEN")
PHONE_NUMBER_ID = os.environ.get("WHATSAPP_PHONE_NUMBER_ID")
VERIFY_TOKEN = os.environ.get("WHATSAPP_VERIFY_TOKEN", "agno_verify_123")

# The chatting agent (Qwen model, with conversation history)
agent = Agent(
    name="whatsapp-bot",
    model=Groq(id="qwen/qwen3.8-27b", max_tokens=1000),
    instructions=[
        "You are a friendly AI assistant chatting on WhatsApp.",
        "Keep replies short and conversational, like real WhatsApp messages.",
        "Maximum 2-3 sentences per reply unless asked for detail.",
    ],
    markdown=False,
    num_history_messages=10, # Remembers the last 10 messages in the current session
)


def send_whatsapp_text(to_waid: str, text: str):
    url = f"https://graph.facebook.com/v21.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to_waid,
        "type": "text",
        "text": {"body": text},
    }
    r = requests.post(url, json=payload, headers=headers, timeout=30)
    print("SEND STATUS:", r.status_code, r.text[:200])


def handle_message(from_waid: str, user_text: str):
    print(f"USER: {user_text}")
    # We use the user's phone number as the session_id so the agent remembers them!
    reply = agent.run(user_text, session_id=from_waid).content
    print(f"BOT: {reply}")
    send_whatsapp_text(from_waid, reply)


# Health check - proves the bot is alive
@app.get("/")
async def root():
    return {"status": "alive", "bot": "whatsapp-agent"}


# Meta calls this GET once to verify your webhook
@app.get("/whatsapp")
async def verify(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
):
    if hub_mode == "subscribe" and hub_verify_token == VERIFY_TOKEN:
        return PlainTextResponse(hub_challenge)
    return PlainTextResponse("Verification failed", status_code=403)


# Meta POSTs every incoming message here
@app.post("/whatsapp")
async def receive(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()
    try:
        value = data["entry"][0]["changes"][0]["value"]
        if "messages" in value:
            msg = value["messages"][0]
            if msg.get("type") == "text" and msg.get("from") != PHONE_NUMBER_ID:
                background_tasks.add_task(
                    handle_message, msg["from"], msg["text"]["body"]
                )
    except Exception as e:
        print("WEBHOOK PARSE ERROR:", e)
    return PlainTextResponse("OK")


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
