import asyncio
import logging
from brain.core.state_machine import StateMachine, NILAState
from brain.ipc.ws_server import NILAIPCServer
from brain.safety.policy import SafetyPolicy
from brain.agent.loop import AgentLoop
from brain.core.config import load_config

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s"
)
logger = logging.getLogger("NILA.Main")

async def main():
    config = load_config()
    logger.info(f"Starting {config.system.name} v{config.system.version} Brain...")

    state_machine = StateMachine()
    ipc_server = NILAIPCServer(
        host=config.ipc.host, 
        port=config.ipc.port, 
        auth_token=config.ipc.auth_token
    )
    safety_policy = SafetyPolicy()

    await ipc_server.start()

    agent = AgentLoop(
        state_machine=state_machine,
        ipc_server=ipc_server,
        safety_policy=safety_policy
    )

    ipc_server.set_agent_loop(agent)

    print("\n--- N.I.L.A. Brain CLI REPL Started ---")
    print("Type your command below (or 'exit' to quit):\n")

    while True:
        try:
            user_input = await asyncio.to_thread(input, "N.I.L.A. > ")
            user_input = user_input.strip()
            
            if not user_input:
                continue
            if user_input.lower() in ["exit", "quit"]:
                logger.info("Exiting N.I.L.A. Brain CLI...")
                break

            await agent.process_user_intent(user_input)

        except (KeyboardInterrupt, EOFError):
            print("\nShutting down...")
            break
        except Exception as e:
            logger.error(f"Error in main loop: {e}", exc_info=True)

    await ipc_server.stop()

if __name__ == "__main__":
    asyncio.run(main())