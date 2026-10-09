from enum import Enum
import logging

logger = logging.getLogger("NILA.StateMachine")

class NILAState(str, Enum):
    IDLE = "IDLE"
    WAKE = "WAKE"
    LISTENING = "LISTENING"
    TRANSCRIBING = "TRANSCRIBING"
    THINKING = "THINKING"
    EXECUTING = "EXECUTING"
    SPEAKING = "SPEAKING"
    ERROR = "ERROR"

class StateMachine:
    def __init__(self, initial_state: NILAState = NILAState.IDLE):
        self._current_state = initial_state
        self._listeners = []

    @property
    def state(self) -> NILAState:
        return self._current_state

    def add_callback(self, callback):
        self._listeners.append(callback)

    async def transition_to(self, new_state: NILAState, reason: str = ""):
        if self._current_state != new_state:
            logger.info(f"State transition: {self._current_state.value} -> {new_state.value} ({reason})")
            self._current_state = new_state
            for cb in self._listeners:
                await cb(self._current_state, reason)
