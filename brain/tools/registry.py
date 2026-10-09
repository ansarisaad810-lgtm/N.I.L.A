import functools
from brain.safety.policy import SafetyTier

class ToolRegistry:
    def __init__(self):
        self._tools = {}

    def register(self, name: str, tier: SafetyTier = SafetyTier.SAFE, description: str = ""):
        def decorator(func):
            desc = description or func.__doc__ or f"Execute {name}"
            self._tools[name] = (func, tier, desc)
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)
            return wrapper
        return decorator

    def add_tool(self, name: str, func, tier: SafetyTier = SafetyTier.SAFE, description: str = ""):
        desc = description or func.__doc__ or f"Execute {name}"
        self._tools[name] = (func, tier, desc)

    def get_tool(self, name: str):
        return self._tools.get(name)

    async def execute(self, name: str, **kwargs):
        tool = self.get_tool(name)
        if not tool:
            return {"ok": False, "error": f"Tool '{name}' not registered"}
        func = tool[0]
        try:
            return func(**kwargs)
        except Exception as e:
            return {"ok": False, "error": str(e)}

registry = ToolRegistry()

from brain.tools.system_control import (
    smart_open, file_search, youtube_search, youtube_play, youtube_control, set_volume, set_reminder,
    send_whatsapp_message, media_control, set_brightness, process_manager
)

registry.add_tool("smart_open", smart_open, tier=SafetyTier.SAFE, description="Launch any app, file, cached file, folder, Control Panel, or open URL.")
registry.add_tool("file_search", file_search, tier=SafetyTier.SAFE, description="Search for files in Downloads, Documents, or Desktop.")
registry.add_tool("youtube_search", youtube_search, tier=SafetyTier.SAFE, description="Only search for videos on YouTube without playing. Use when user says 'search'.")
registry.add_tool("youtube_play", youtube_play, tier=SafetyTier.SAFE, description="Search and automatically play the official/original video on YouTube. Use when user says 'play'.")
registry.add_tool("youtube_control", youtube_control, tier=SafetyTier.SAFE, description="Control active YouTube playback: fast_forward, rewind, speed_up, speed_down, mute, fullscreen.")
registry.add_tool("set_volume", set_volume, tier=SafetyTier.SAFE, description="Set system audio volume 0-100.")
registry.add_tool("set_reminder", set_reminder, tier=SafetyTier.SAFE, description="Set a local reminder timer.")
registry.add_tool("send_whatsapp_message", send_whatsapp_message, tier=SafetyTier.SAFE, description="Send a WhatsApp message.")
registry.add_tool("media_control", media_control, tier=SafetyTier.SAFE, description="Control global system media playback: play, pause, next, previous, mute.")
registry.add_tool("set_brightness", set_brightness, tier=SafetyTier.SAFE, description="Set screen brightness 0-100%.")
registry.add_tool("process_manager", process_manager, tier=SafetyTier.SAFE, description="Manage active processes: list running apps, or kill/close a process by name.")