import asyncio
from collections import defaultdict
from typing import Callable, Awaitable, Any

class EventBus:
    def __init__(self):
        self._subscribers = defaultdict(list)

    def subscribe(self, event_type: str, callback: Callable[[Any], Awaitable[None]]):
        self._subscribers[event_type].append(callback)

    async def publish(self, event_type: str, payload: Any):
        if event_type in self._subscribers:
            tasks = [cb(payload) for cb in self._subscribers[event_type]]
            await asyncio.gather(*tasks)
