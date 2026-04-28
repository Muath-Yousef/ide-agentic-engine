import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import yaml
from pydantic import BaseModel


class APIKey(BaseModel):
    value: str
    status: str = "active"  # "active", "cooldown", "exhausted"
    retry_after: Optional[datetime] = None


class ServiceKeys(BaseModel):
    keys: List[APIKey]


class KeyPoolConfig(BaseModel):
    services: Dict[str, ServiceKeys]


class APIKeyPool:
    """
    Manages API keys for external services and LLM providers.
    Supports automatic key rotation, cooldown periods for rate limits,
    and permanent exhaustion marking.
    """

    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.config_path = os.path.join(project_root, "profiles/api_keys.yaml")
        else:
            self.config_path = config_path
        self.config: KeyPoolConfig = self._load_config()
        self._indices: Dict[str, int] = {}  # Track round-robin index per service

    def _load_config(self) -> KeyPoolConfig:
        if not os.path.exists(self.config_path):
            # Return empty config if file doesn't exist
            return KeyPoolConfig(services={})

        with open(self.config_path, "r") as f:
            data = yaml.safe_load(f) or {}
            return KeyPoolConfig(**data)

    def _save_config(self):
        """Save the current state back to YAML."""
        with open(self.config_path, "w") as f:
            yaml.dump(self.config.model_dump(mode="json"), f, default_flow_style=False)

    def get_key(self, service_name: str) -> Optional[str]:
        """
        Get the next available active key for a service using Round-Robin rotation.
        Automatically reactivates cooldown keys if their retry_after time has passed.
        """
        if service_name not in self.config.services:
            return None

        service = self.config.services[service_name]
        if not service.keys:
            return None

        now = datetime.utcnow()
        start_index = self._indices.get(service_name, 0)
        num_keys = len(service.keys)

        # Try all keys starting from start_index
        for i in range(num_keys):
            idx = (start_index + i) % num_keys
            key_obj = service.keys[idx]

            # Check for reactivation
            if key_obj.status == "cooldown" and key_obj.retry_after:
                if now >= key_obj.retry_after:
                    key_obj.status = "active"
                    key_obj.retry_after = None
                    self._save_config()

            if key_obj.status == "active":
                # Update index for next time
                self._indices[service_name] = (idx + 1) % num_keys
                return key_obj.value

        return None

    def mark_exhausted(
        self,
        service_name: str,
        key_value: str,
        is_rate_limit: bool = True,
        cooldown_seconds: int = 60,
    ):
        """
        Mark a key as exhausted (permanent) or cooldown (temporary).
        """
        if service_name not in self.config.services:
            return

        service = self.config.services[service_name]

        for key_obj in service.keys:
            if key_obj.value == key_value:
                if is_rate_limit:
                    key_obj.status = "cooldown"
                    key_obj.retry_after = datetime.utcnow() + timedelta(seconds=cooldown_seconds)
                else:
                    key_obj.status = "exhausted"
                    key_obj.retry_after = None
                self._save_config()
                return
