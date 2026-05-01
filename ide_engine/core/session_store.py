import json
import logging
from typing import Any, Dict, Optional

import redis

logger = logging.getLogger(__name__)


class SessionStore:
    """
    Stores LangGraph orchestration state in Redis to support
    Human-in-the-Loop (HITL) pauses and resumes.
    """

    _in_memory_store: Dict[str, str] = {}

    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 1):
        try:
            self.client = redis.Redis(host=host, port=port, db=db, decode_responses=True)
            self.client.ping()
            self.enabled = True
        except redis.ConnectionError:
            logger.warning(
                "Redis not reachable. Session storage will use in-memory fallback (not persistent across restarts)."
            )
            self.enabled = False

    def save_session(self, session_id: str, state: Dict[str, Any], ttl_seconds: int = 86400):
        """Save AgentState to Redis."""
        try:
            # messages need to be serialized carefully if they are Pydantic objects or custom dicts
            # We assume state is JSON serializable
            state_json = json.dumps(state)
            if self.enabled:
                self.client.setex(f"session:{session_id}", ttl_seconds, state_json)
            else:
                self._in_memory_store[session_id] = state_json
        except Exception as e:
            logger.error(f"Failed to save session {session_id}: {e}")

    def load_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load AgentState from Redis."""
        try:
            if self.enabled:
                state_json = self.client.get(f"session:{session_id}")
            else:
                state_json = self._in_memory_store.get(session_id)

            if state_json:
                return json.loads(state_json)
            return None
        except Exception as e:
            logger.error(f"Failed to load session {session_id}: {e}")
            return None

    def delete_session(self, session_id: str):
        """Delete a session after completion or rejection."""
        if self.enabled:
            self.client.delete(f"session:{session_id}")
        else:
            self._in_memory_store.pop(session_id, None)
