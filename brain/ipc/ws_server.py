import asyncio
import json
import logging
from typing import Set
import websockets
from websockets.server import WebSocketServerProtocol

logger = logging.getLogger("NILA.IPC")

class NILAIPCServer:
    def __init__(self, host: str = "127.0.0.1", port: int = 8765, auth_token: str = ""):
        self.host = host
        self.port = port
        self.auth_token = auth_token
        self.clients: Set[WebSocketServerProtocol] = set()
        self.server = None
        self.agent_loop = None

    def set_agent_loop(self, agent_loop):
        self.agent_loop = agent_loop

    async def start(self):
        self.server = await websockets.serve(self._handler, self.host, self.port)
        logger.info(f"N.I.L.A. IPC WebSocket server running on ws://{self.host}:{self.port}")

    async def stop(self):
        if self.server:
            self.server.close()
            await self.server.wait_closed()

    async def _handler(self, websocket: WebSocketServerProtocol, path: str = ""):
        self.clients.add(websocket)
        logger.info(f"Client connected: {websocket.remote_address}")
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    msg_type = data.get("type")
                    payload = data.get("payload", {})
                    
                    if msg_type == "user_intent":
                        text = payload.get("text", "")
                        if text and self.agent_loop:
                            asyncio.create_task(self.agent_loop.process_user_intent(text))
                except Exception as e:
                    logger.error(f"Error handling IPC message: {e}")
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.clients.remove(websocket)
            logger.info("Client disconnected")

    async def broadcast(self, envelope):
        if not self.clients:
            return
        
        if hasattr(envelope, "model_dump_json"):
            msg = envelope.model_dump_json()
        elif hasattr(envelope, "json"):
            msg = envelope.json()
        elif isinstance(envelope, dict):
            msg = json.dumps(envelope)
        else:
            msg = str(envelope)

        for client in list(self.clients):
            try:
                await client.send(msg)
            except Exception as e:
                logger.warning(f"Failed to send to client: {e}")