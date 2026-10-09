import json
import logging
from enum import Enum
from typing import Dict, Any

class SafetyTier(Enum):
    SAFE = 1
    NORMAL = 2
    ELEVATED = 3
    CRITICAL = 4

class SafetyPolicy:
    def __init__(self, audit_log_path: str = "brain/safety/audit_log.jsonl"):
        self.audit_log_path = audit_log_path
        self.logger = logging.getLogger("NILA.Safety")

    def log_action(self, tool_name: str, tier: Any, args: Dict[str, Any], approved: bool = True):
        # Extract numeric value whether tier is an Enum or a raw integer
        tier_val = tier.value if hasattr(tier, "value") else int(tier)
        
        entry = {
            "tool_name": tool_name,
            "tier": tier_val,
            "args": args,
            "approved": approved
        }
        
        self.logger.info(f"Audit Log Entry: {entry}")
        
        try:
            with open(self.audit_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            self.logger.error(f"Failed to write audit log: {e}")
