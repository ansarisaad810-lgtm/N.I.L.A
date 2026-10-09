import pytest
from brain.tools.registry import registry
from brain.safety.policy import SafetyTier

@pytest.mark.asyncio
async def test_tool_registration_and_execution():
    @registry.register("test_ping", SafetyTier.SAFE, "Test ping tool")
    def ping(val: str):
        return f"pong {val}"

    tool = registry.get_tool("test_ping")
    assert tool is not None
    
    result = await registry.execute("test_ping", val="hello")
    assert result["ok"] is True
    assert result["data"] == "pong hello"
