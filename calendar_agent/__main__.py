import os
import time
from datetime import datetime
from uuid import uuid4
from zoneinfo import ZoneInfo
from datapizza.tracing import ContextTracing
from opentelemetry import trace
from .agent import create_calendar_agent
from .telemetry import render_turn_summary, summarize_spans
from .tools import init_db, seed_db, _get_db_path
from .utils import env_truthy

def _tracing_enabled() -> bool:
    return os.getenv("CALENDAR_TRACING", "").strip().lower() in {"1", "true"}

def _clear_agent_memory(agent) -> None:
    if hasattr(agent, "memory") and agent.memory:
        agent.memory.clear()
        return
    if hasattr(agent, "_memory") and agent._memory:
        agent._memory.clear()

def main():
    init_db()
    seed_db()
    structured = env_truthy("CALENDAR_STRUCTURED_OUTPUT", "0")
    
    print("--- Calendar Assistant REPL ---")
    print("Type your request or '/exit' to quit.")
    
    agent = create_calendar_agent()
    session_id = str(uuid4())
    tracing_enabled = _tracing_enabled()
    tracer = trace.get_tracer(__name__) if tracing_enabled else None
    
    max_turns = 2 if structured else 15
    structured_turn_count = 0
    for turn in range(max_turns):
        try:
            user_input = input("\nUser: ").strip()
        except EOFError:
            break
            
        if user_input.lower() == "/exit":
            if structured:
                _clear_agent_memory(agent)
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
                        start_time = time.perf_counter()
                        response = agent.run(context + user_input)
                        duration_ms = (time.perf_counter() - start_time) * 1000

                    if span is not None and response is not None:
                        usage = getattr(response, "usage", None)
                        if usage is not None:
                            span.set_attribute(
                                "turn.prompt_tokens", int(usage.prompt_tokens or 0)
                            )
                            span.set_attribute(
                                "turn.completion_tokens",
                                int(usage.completion_tokens or 0),
                            )
                            span.set_attribute(
                                "turn.cached_tokens", int(usage.cached_tokens or 0)
                            )
                            span.set_attribute(
                                "turn.total_tokens",
                                int(
                                    (usage.prompt_tokens or 0)
                                    + (usage.completion_tokens or 0)
                                    + (usage.cached_tokens or 0)
                                ),
                            )
                        span.set_attribute("turn.duration_ms", round(duration_ms, 2))

                    summary = summarize_spans(ctx.get_spans())
                    if span is not None:
                        cache_savings = summary["cache_savings"]
                        span.set_attribute(
                            "cache.saved_prompt_tokens",
                            int(cache_savings.prompt_tokens),
                        )
                        span.set_attribute(
                            "cache.saved_completion_tokens",
                            int(cache_savings.completion_tokens),
                        )
                        span.set_attribute(
                            "cache.saved_cached_tokens",
                            int(cache_savings.cached_tokens),
                        )
                        span.set_attribute(
                            "cache.saved_total_tokens",
                            int(cache_savings.total_tokens),
                        )
                        span.set_attribute(
                            "tool.calls", int(summary.get("tool_calls", 0))
                        )
                        span.set_attribute(
                            "tool.total_duration_ms",
                            float(summary.get("tool_total_ms", 0.0)),
                        )

                    render_turn_summary(
                        summary,
                        duration_ms=duration_ms,
                        usage=getattr(response, "usage", None),
                    )
            else:
                now_rome = datetime.now(ZoneInfo("Europe/Rome"))
                context = f"[CURRENT_TIME_ROME={now_rome.isoformat()}] "
                response = agent.run(context + user_input)

            if structured:
                print(f"\n{response.text}")
            else:
                print(f"\nAssistant: {response.text}")

            if structured:
                structured_turn_count += 1
                if structured_turn_count >= 2:
                    _clear_agent_memory(agent)
                    print("Structured mode limit reached (2 turns). Memory cleared. Restart session for more.")
                    break
        except Exception as e:
            print(f"\nError: {e}")
    else:
        print(f"\nMax conversation turns ({max_turns}) reached. Ending session.")


if __name__ == "__main__":
    main()
