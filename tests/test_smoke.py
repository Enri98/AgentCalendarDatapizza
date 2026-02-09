import pytest
import os
from calendar_agent.agent import create_calendar_agent

def test_agent_instantiation():
    """Basic test to ensure the agent can be instantiated."""
    # We mock the API key if missing so instantiation doesn't fail 
    # (though GoogleClient might check it on init)
    if not os.getenv("GOOGLE_API_KEY"):
        os.environ["GOOGLE_API_KEY"] = "mock_key"
    
    agent = create_calendar_agent()
    assert agent is not None
    assert len(agent.tools) == 4

@pytest.mark.skipif(not os.getenv("GOOGLE_API_KEY") or os.getenv("GOOGLE_API_KEY") == "mock_key", 
                    reason="Valid GOOGLE_API_KEY not set")
def test_agent_run_real():
    """Test agent run with a simple prompt (requires real API key)."""
    agent = create_calendar_agent()
    response = agent.run("Hello, who are you?")
    assert isinstance(response, str)

