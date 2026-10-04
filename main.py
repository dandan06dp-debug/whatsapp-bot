import os
from dotenv import load_dotenv
from agno.agent import Agent
from agno.models.groq import Groq
from agno.os.app import AgentOS
from agno.os.interfaces.whatsapp import Whatsapp

load_dotenv()

# 1. Define the Agent using Groq's Qwen model
# qwen/qwen3-32b is extremely fast and very smart
simple_agent = Agent(
    name="Simple WhatsApp Bot",
    model=Groq(id="qwen/qwen3-32b"), 
    markdown=False, 
    instructions="You are a friendly and concise WhatsApp assistant. Keep your replies short, natural, and conversational.",
)

# 2. Wrap in AgentOS with the built-in Whatsapp interface
agent_os = AgentOS(
    agents=[simple_agent],
    interfaces=[Whatsapp(agent=simple_agent)],
)

# 3. Get the FastAPI application
app = agent_os.get_app()

if __name__ == "__main__":
    # Render automatically assigns a dynamic port via the $PORT environment variable
    port = int(os.environ.get("PORT", 8000))
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=port)
