import os
from agno.agent import Agent
from agno.db.sqlite import SqliteDb
from agno.models.groq import Groq
from agno.os.app import AgentOS
from agno.os.interfaces.whatsapp import Whatsapp

# Creates a local database to remember your conversations
agent_db = SqliteDb(db_file="whatsapp_memory.db")

basic_agent = Agent(
    name="WhatsApp AI",
    model=Groq(id="qwen/qwen3.8-27b", max_tokens=1000),
    db=agent_db,
    add_history_to_context=True,
    num_history_runs=5,
    add_datetime_to_context=True,
    instructions=[
        "You are a friendly AI assistant chatting on WhatsApp.",
        "Keep replies short and conversational, like real WhatsApp messages.",
    ],
    markdown=False,
)

# AgentOS automatically handles webhooks and Meta's security signatures!
agent_os = AgentOS(
    agents=[basic_agent],
    interfaces=[Whatsapp(agent=basic_agent)],
)

app = agent_os.get_app()

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
