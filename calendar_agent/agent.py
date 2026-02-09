import os
from dotenv import load_dotenv
from datapizza.clients.google import GoogleClient
from datapizza.memory import Memory
from datapizza.agents import Agent
from .tools import list_events, add_event, update_event, delete_events

load_dotenv()

# Silence Datapizza step-by-step logging by default
if "DATAPIZZA_LOG_LEVEL" not in os.environ:
    os.environ["DATAPIZZA_LOG_LEVEL"] = "WARN"
if "DATAPIZZA_AGENT_LOG_LEVEL" not in os.environ:
    os.environ["DATAPIZZA_AGENT_LOG_LEVEL"] = "WARN"

def create_calendar_agent():
    api_key = os.getenv("GOOGLE_API_KEY")
    model = os.getenv("MODEL", "gemini-2.0-flash")
    
    if not api_key:
        # In a real app we might raise an error, but for scaffolding we'll allow it 
        # to exist even if it will fail on run.
        pass

    client = GoogleClient(api_key=api_key, model=model)
    memory = Memory()
    
    system_prompt = (
        "You are a concise Calendar Assistant.\n"
        "Rules:\n"
        "1. Never invent event IDs. Only use IDs returned by tools.\n"
        "2. Use tools for all CRUD operations (list, add, update, delete).\n"
        "3. If a time range or event ID is missing or ambiguous, ask a concise clarifying question.\n"
        "4. If the user refers to events by title for update/delete, first call list_events for the inferred range to obtain IDs; never guess IDs.\n"
        "5. Be concise in your responses."
    )
    
    agent = Agent(
        name="CalendarAssistant",
        client=client,
        memory=memory,
        stateless=False,
        max_steps=8,
        system_prompt=system_prompt,
        tools=[list_events, add_event, update_event, delete_events]
    )
    
    return agent
