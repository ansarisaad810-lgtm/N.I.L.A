import os
import asyncio
import json
from typing import List, Dict, Any
from groq import Groq

class GroqProvider:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("GROQ_API_KEY", "")
        self.model_name = "openai/gpt-oss-20b"
        self.client = None
        
        if self.api_key and "YOUR_GROQ_API_KEY" not in self.api_key:
            self.client = Groq(api_key=self.api_key)

    def _convert_registry_to_tools(self, tool_registry: dict) -> List[Dict[str, Any]]:
        tools = []
        for name, entry in tool_registry.items():
            doc = entry[2] if isinstance(entry, tuple) and len(entry) > 2 else f"Execute {name}"
            
            params = {}
            required = []
            
            if name == "smart_open":
                params = {"target": {"type": "string", "description": "App name, cached file, folder, or URL"}}
                required = ["target"]
            elif name == "file_search":
                params = {
                    "filename": {"type": "string", "description": "File name or keyword"},
                    "search_dir": {"type": "string", "description": "Folder to search"}
                }
                required = ["filename"]
            elif name == "youtube_search":
                params = {"query": {"type": "string", "description": "Query to search on YouTube without auto-playing"}}
                required = ["query"]
            elif name == "youtube_play":
                params = {"query": {"type": "string", "description": "Video title or query to auto-play (prioritizing official content)"}}
                required = ["query"]
            elif name == "youtube_control":
                params = {
                    "action": {"type": "string", "description": "Action: fast_forward, rewind, speed_up, speed_down, mute, fullscreen"},
                    "count": {"type": "integer", "description": "Number of times to execute action (default 1)"}
                }
                required = ["action"]
            elif name == "set_volume":
                params = {"level": {"type": "integer", "description": "Volume 0-100"}}
                required = ["level"]
            elif name == "set_reminder":
                params = {
                    "message": {"type": "string", "description": "Reminder text"},
                    "delay_seconds": {"type": "integer", "description": "Delay in seconds"}
                }
                required = ["message", "delay_seconds"]
            elif name == "send_whatsapp_message":
                params = {
                    "phone_number": {"type": "string", "description": "Phone number with country code"},
                    "message": {"type": "string", "description": "Message text"}
                }
                required = ["phone_number", "message"]
            elif name == "media_control":
                params = {"action": {"type": "string", "description": "Action: play, pause, next, previous, or mute"}}
                required = ["action"]
            elif name == "set_brightness":
                params = {"level": {"type": "integer", "description": "Brightness percentage 0-100"}}
                required = ["level"]
            elif name == "process_manager":
                params = {
                    "action": {"type": "string", "description": "Action: 'list' or 'close'"},
                    "process_name": {"type": "string", "description": "Target process name if action is close"}
                }
                required = ["action"]

            tools.append({
                "type": "function",
                "function": {
                    "name": name,
                    "description": doc,
                    "parameters": {"type": "object", "properties": params, "required": required}
                }
            })
        return tools

    async def generate_response_with_tools(self, prompt: str, tool_registry: dict, history: List[Dict[str, str]]) -> dict:
        if not self.client:
            return {"type": "text", "content": "[Groq Placeholder]: Set a valid Groq API key in config.toml."}

        try:
            sys_instruct = (
                "You are N.I.L.A., a localized desktop assistant with persistent memory.\n"
                "Use 'youtube_search' ONLY when the user explicitly asks to search or find videos on YouTube.\n"
                "Use 'youtube_play' when the user explicitly asks to play a video or music on YouTube."
            )
            
            messages = [{"role": "system", "content": sys_instruct}]
            messages.extend(history)
            messages.append({"role": "user", "content": prompt})

            tools = self._convert_registry_to_tools(tool_registry)
            
            loop = asyncio.get_event_loop()
            completion = await loop.run_in_executor(
                None,
                lambda: self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    tools=tools,
                    tool_choice="auto",
                    temperature=0.1,
                )
            )
            
            msg = completion.choices[0].message
            if msg.tool_calls:
                call = msg.tool_calls[0]
                return {
                    "type": "tool_call",
                    "name": call.function.name,
                    "args": json.loads(call.function.arguments)
                }
            
            return {"type": "text", "content": msg.content or "Done."}
        except Exception as e:
            return {"type": "text", "content": f"Groq API Error: {str(e)}"}