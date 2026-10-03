import os
import sys
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

# Helper function to force logs to show up immediately in Render
def log(message):
    sys.stdout.write(f"{message}\n")
    sys.stdout.flush()

# The chatting agent (Qwen model)
agent = Agent(
    name="whatsapp-bot",
    model=Groq(id="qwen/qwen3.8-27b", max_tokens=1000),
    instructions=[
        "You are a friendly AI assistant chatting on WhatsApp.",
        "Keep replies short and conversational, like real WhatsApp messages.",
        "Maximum 2-3 sentences per reply unless asked for detail.",
    ],
    markdown=False,
    num_history_messages=10,
)


def send_whatsapp_text(to_waid: str, text: str):
    log(f"SENDING TO WHATSAPP: {text}")
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
    log(f"WHATSAPP API STATUS: {r.status_code} - {r.text[:200]}")


def handle_message(from_waid: str, user_text: str):
    try:
        log(f"USER SAID: {user_text}")
        
        # Check if keys are loaded
        if not ACCESS_TOKEN:
            log("ERROR: WHATSAPP_ACCESS_TOKEN is missing in Render!")
            return
        if not PHONE_NUMBER_ID:
            log("ERROR: WHATSAPP_PHONE_NUMBER_ID is missing in Render!")
            return

        # Run the agent
        response = agent.run(user_text, session_id=from_waid)
        reply = response.content if response and response.content else "Sorry, I had a brain glitch."
        
        log(f"BOT REPLIED: {reply}")
        send_whatsapp_text(from_waid, reply)
        
    except Exception as e:
        log(f"!!! ERROR IN AI BRAIN: {e}")


@app.get("/")
async def root():
    return {"status": "alive", "bot": "whatsapp-agent"}


@app.get("/whatsapp")
async def verify(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
):
    log(f"META VERIFY REQUEST: mode={hub_mode}, token={hub_verify_token}")
    if hub_mode == "subscribe" and hub_verify_token == VERIFY_TOKEN:
        return PlainTextResponse(hub_challenge)
    return PlainTextResponse("Verification failed", status_code=403)


@app.post("/whatsapp")
async def receive(request: Request, background_tasks: BackgroundTasks):
    try:
        data = await request.json()
        log(f"INCOMING WEBHOOK FROM META!")
        
        value = data["entry"][0]["changes"][0]["value"]
        
        if "messages" in value:
            msg = value["messages"][0]
            if msg.get("type") == "text" and msg.get("from") != PHONE_NUMBER_ID:
                log(f"FOUND A TEXT MESSAGE FROM {msg['from']}")
                background_tasks.add_task(
                    handle_message, msg["from"], msg["text"]["body"]
                )
        else:
            log("Received a status update, not a new message.")
            
    except Exception as e:
        log(f"WEBHOOK PARSE ERROR: {e}")
    return PlainTextResponse("OK")


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
