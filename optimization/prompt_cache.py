import hashlib
import json
import redis
from typing import Any, Dict, Optional

class PromptCache:
    """
    Redis-based LLM caching layer to achieve $0 cost on repeat queries.
    """
    def __init__(self, host: str = 'localhost', port: int = 6379, db: int = 0):
        try:
            self.client = redis.Redis(host=host, port=port, db=db, decode_responses=True)
            # Test connection
            self.client.ping()
            self.enabled = True
        except redis.ConnectionError:
            print("Warning: Redis not reachable. Caching disabled.")
            self.enabled = False

    def _generate_key(self, model: str, messages: list[Dict[str, str]], tools: Optional[list] = None) -> str:
        """Generate a SHA256 hash for the cache key based on inputs."""
        payload = {
            "model": model,
            "messages": messages,
            "tools": tools or []
        }
        payload_str = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(payload_str.encode()).hexdigest()

    def get(self, model: str, messages: list[Dict[str, str]], tools: Optional[list] = None) -> Optional[str]:
        if not self.enabled:
            return None
        key = self._generate_key(model, messages, tools)
        return self.client.get(key)

    def set(self, model: str, messages: list[Dict[str, str]], result: str, ttl_seconds: int = 3600, tools: Optional[list] = None):
        if not self.enabled:
            return
        key = self._generate_key(model, messages, tools)
        self.client.setex(key, ttl_seconds, result)
