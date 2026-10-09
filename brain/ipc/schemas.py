import time
import uuid
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

class IPCEnvelope(BaseModel):
    type: str
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    ts: float = Field(default_factory=time.time)
    payload: Dict[str, Any] = Field(default_factory=dict)

class StateChangePayload(BaseModel):
    state: str
    reason: Optional[str] = ""

class ToolStartPayload(BaseModel):
    tool_name: str
    args: Dict[str, Any]

class ToolEndPayload(BaseModel):
    tool_name: str
    result: Dict[str, Any]
    duration_ms: float

class ConfirmRequestPayload(BaseModel):
    request_id: str
    action_description: str
    tier: int
