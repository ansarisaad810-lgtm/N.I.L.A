import time
from brain.core.state_machine import StateMachine, NILAState
from brain.tools.registry import registry
from brain.safety.policy import SafetyPolicy
from brain.ipc.ws_server import NILAIPCServer
from brain.ipc.schemas import IPCEnvelope, ToolStartPayload, ToolEndPayload
from brain.agent.providers.groq import GroqProvider
from brain.core.config import load_config
from brain.core.memory import memory

class AgentLoop:
    def __init__(self, state_machine: StateMachine, ipc_server: NILAIPCServer, safety_policy: SafetyPolicy):
        self.sm = state_machine
        self.ipc = ipc_server
        self.safety = safety_policy
        
        config = load_config()
        self.llm = GroqProvider(api_key=config.agent.groq_api_key)

    async def process_user_intent(self, text: str):
        await self.sm.transition_to(NILAState.THINKING, f"Processing user input: {text}")

        # 1. Retrieve recent chat history from SQLite memory
        history = memory.get_recent_history(limit=10)

        # 2. Query LLM with history and tool registry
        llm_res = await self.llm.generate_response_with_tools(text, registry._tools, history)

        if llm_res["type"] == "tool_call":
            tool_name = llm_res["name"]
            tool_args = llm_res["args"]
            res = await self._run_tool(tool_name, tool_args)
            
            out_detail = res.get("data") if isinstance(res, dict) else str(res)
            response_text = f"Yes, I executed [{tool_name}]: {out_detail}"
        else:
            response_text = llm_res["content"]

        # 3. Store conversation turn in SQLite memory
        memory.add_message("user", text)
        memory.add_message("assistant", response_text)

        print(f"\n[N.I.L.A.]: {response_text}")

        await self.ipc.broadcast(IPCEnvelope(
            type="assistant_token",
            payload={"text": response_text}
        ))

        await self.sm.transition_to(NILAState.IDLE, "Completed agent loop cycle")

    async def _run_tool(self, name: str, kwargs: dict) -> dict:
        tool_entry = registry.get_tool(name)
        if not tool_entry:
            return {"ok": False, "error": f"Tool {name} not found"}

        _, tier, _ = tool_entry
        self.safety.log_action(name, tier, kwargs, approved=True)

        await self.sm.transition_to(NILAState.EXECUTING, f"Executing tool: {name}")
        await self.ipc.broadcast(IPCEnvelope(
            type="tool_start",
            payload=ToolStartPayload(tool_name=name, args=kwargs).model_dump()
        ))

        start_time = time.time()
        result = await registry.execute(name, **kwargs)
        duration = (time.time() - start_time) * 1000

        if not isinstance(result, dict):
            result = {"ok": True, "data": str(result)}

        await self.ipc.broadcast(IPCEnvelope(
            type="tool_end",
            payload=ToolEndPayload(tool_name=name, result=result, duration_ms=duration).model_dump()
        ))
        return result
