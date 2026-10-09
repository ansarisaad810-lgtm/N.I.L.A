import os
import tomllib
from typing import Optional
from pydantic import BaseModel, Field

class SystemConfig(BaseModel):
    name: str = "N.I.L.A."
    version: str = "0.1.0"
    environment: str = "development"

class IPCConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8765
    auth_token: str = "nila_local_dev_token_2026"

class AgentConfig(BaseModel):
    max_steps: int = 5
    llm_provider: str = "groq"
    user_name: str = "Sir"
    groq_api_key: str = Field(default="YOUR_GROQ_API_KEY_HERE")

class SafetyConfig(BaseModel):
    enable_audit_log: bool = True
    audit_log_path: str = "brain/safety/audit_log.jsonl"

class NILAConfig(BaseModel):
    system: SystemConfig = Field(default_factory=SystemConfig)
    ipc: IPCConfig = Field(default_factory=IPCConfig)
    agent: AgentConfig = Field(default_factory=AgentConfig)
    safety: SafetyConfig = Field(default_factory=SafetyConfig)

def load_config(config_path: str = "config.toml") -> NILAConfig:
    if not os.path.exists(config_path):
        return NILAConfig()
    
    with open(config_path, "rb") as f:
        data = tomllib.load(f)
    return NILAConfig(**data)
