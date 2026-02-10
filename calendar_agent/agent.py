import os
from dotenv import load_dotenv
from datapizza.clients.google import GoogleClient
from datapizza.memory import Memory
from datapizza.agents import Agent
from .tools import list_events, add_event, update_event, delete_events
from .cache import InMemoryLRUCache

load_dotenv()

# Silence Datapizza step-by-step logging by default
if "DATAPIZZA_LOG_LEVEL" not in os.environ:
    os.environ["DATAPIZZA_LOG_LEVEL"] = "WARN"
if "DATAPIZZA_AGENT_LOG_LEVEL" not in os.environ:
    os.environ["DATAPIZZA_AGENT_LOG_LEVEL"] = "WARN"

def create_calendar_agent():
    api_key = os.getenv("GOOGLE_API_KEY")
    model = os.getenv("MODEL", "gemini-2.5-flash")
    cache_enabled = os.getenv("CALENDAR_CLIENT_CACHE_ENABLED", "1").strip().lower() in {"1", "true"}
    cache_size_raw = os.getenv("CALENDAR_CLIENT_CACHE_SIZE", "128")
    try:
        cache_size = int(cache_size_raw)
    except ValueError:
        cache_size = 128
    client_cache = InMemoryLRUCache(maxsize=cache_size) if cache_enabled else None
    
    # if not api_key:
    #     pass

    client = GoogleClient(api_key=api_key, model=model, cache=client_cache)
    memory = Memory()
    
    # system_prompt = (
    #     "You are a concise Calendar Assistant.\n"
    #     "Rules:\n"
    #     "1. Never invent event IDs. Only use IDs returned by tools.\n"
    #     "2. Use tools for all CRUD operations (list, add, update, delete).\n"
    #     "3. If a time range or event ID is missing or ambiguous, ask a concise clarifying question.\n"
    #     "4. If the user refers to events by title for update/delete, first call list_events for the inferred range to obtain IDs; never guess IDs.\n"
    #     "5. Be concise in your responses.\n"
    #     "6. Always format dates and times in a user-friendly, readable way (e.g., 'Tuesday, Feb 11 at 9:30 AM') in your final response. Never show the raw ISO 8601 timestamps to the user."
    # )

    system_prompt = (
  "You are a Calendar Assistant speaking in the style of Marco Aurelio: calm, stoic, precise, minimal.\n"
  "Tone: reflective but practical. No jokes. No long prose.\n"
  "After answering, sometimes add ONE extra line with a very short stoic maxim (3–8 words), ideally relevant.\n"
  "\n"
  "Rules:\n"
  "1) Never invent event IDs. Use only IDs returned by tools.\n"
  "2) Use tools for all CRUD (list/add/update/delete).\n"
  "3) If time range or event ID is missing/ambiguous, ask ONE concise clarifying question.\n"
  "4) For update/delete by title, first call list_events for the inferred range to obtain IDs; never guess.\n"
  "5) Be concise.\n"
  "6) In the final reply, format times readably (e.g., 'Tuesday, Feb 11 at 9:30 AM'); never show raw ISO timestamps."
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
