import pytest
import os
from calendar_agent.agent import create_calendar_agent

def test_agent_instantiation():
    """Basic test to ensure the agent can be instantiated."""
    agent = create_calendar_agent()
    assert agent is not None
    assert len(agent.tools) == 4

@pytest.mark.skipif(not os.getenv("GOOGLE_API_KEY"), reason="GOOGLE_API_KEY not set")
def test_agent_run_stub():
    """Test agent run with a simple prompt (requires API key)."""
    agent = create_calendar_agent()
    # This should work if the client is valid, even if it just returns the tool stub response
    response = agent.run("Hello")
    assert isinstance(response, str)
