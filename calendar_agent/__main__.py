import os
from datetime import datetime
from uuid import uuid4
from zoneinfo import ZoneInfo
from datapizza.tracing import ContextTracing
from opentelemetry import trace
from .agent import create_calendar_agent
from .tools import init_db, seed_db, _get_db_path

def _tracing_enabled() -> bool:
    return os.getenv("CALENDAR_TRACING", "").strip().lower() in {"1", "true"}

def main():
    init_db()
    seed_db()
    
    print("--- Calendar Assistant REPL ---")
    print("Type your request or '/exit' to quit.")
    
    agent = create_calendar_agent()
    session_id = str(uuid4())
    tracing_enabled = _tracing_enabled()
    tracer = trace.get_tracer(__name__) if tracing_enabled else None
    
    max_turns = 15
    for turn in range(max_turns):
        try:
            user_input = input("\nUser: ").strip()
        except EOFError:
            break
            
        if user_input.lower() == "/exit":
            print("Goodbye!")
            break
        
        if not user_input:
            continue
            
        try:
            if tracing_enabled:
                with ContextTracing().trace("calendar.turn") as ctx:
                    span = trace.get_current_span()
                    if span is not None:
                        span.set_attribute("session_id", session_id)
                        span.set_attribute("turn_index", turn)
                        span.set_attribute("model", os.getenv("MODEL", ""))
                        span.set_attribute("user_input_length", len(user_input))
                        span.set_attribute("db_path", _get_db_path())

                    with tracer.start_as_current_span("timeparse"):
                        now_rome = datetime.now(ZoneInfo("Europe/Rome"))
                        context = f"[CURRENT_TIME_ROME={now_rome.isoformat()}] "

                    with tracer.start_as_current_span("agent.run"):
                        response = agent.run(context + user_input)
            else:
                now_rome = datetime.now(ZoneInfo("Europe/Rome"))
                context = f"[CURRENT_TIME_ROME={now_rome.isoformat()}] "
                response = agent.run(context + user_input)

            print(f"\nAssistant: {response.text}")
        except Exception as e:
            print(f"\nError: {e}")
    else:
        print("\nMax conversation turns (15) reached. Ending session.")


if __name__ == "__main__":
    main()
