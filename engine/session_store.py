"""
Session Store — Redis-backed persistence for AgentState across invocations.

Each session is a JSON blob stored under ``session:{session_id}`` with a
configurable TTL (default 24 h).  Provides get / set / delete / list helpers.
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from core.cache import get_cache

logger = logging.getLogger(__name__)

_DEFAULT_TTL: int = 86_400  # 24 hours
_KEY_PREFIX: str = "session"


class SessionStore:
    """CRUD wrapper for LangGraph AgentState in Redis."""

    def __init__(self, ttl: int = _DEFAULT_TTL) -> None:
        self._cache = get_cache()
        self._ttl = ttl

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @staticmethod
    def new_session_id() -> str:
        """Generate a fresh session UUID."""
        return str(uuid.uuid4())

    async def save(self, session_id: str, state: dict[str, Any]) -> None:
        """Persist *state* under *session_id* with the configured TTL."""
        key = self._key(session_id)
        payload = json.dumps(state, default=str)
        await self._cache.set(key, payload, ttl=self._ttl)
        logger.debug("Session saved: %s (%d bytes)", session_id, len(payload))

    async def load(self, session_id: str) -> dict[str, Any] | None:
        """
        Load state for *session_id*.

        Returns ``None`` if the session has expired or never existed.
        """
        key = self._key(session_id)
        raw = await self._cache.get(key)
        if raw is None:
            logger.debug("Session not found: %s", session_id)
            return None
        state: dict[str, Any] = json.loads(raw)
        logger.debug("Session loaded: %s", session_id)
        return state

    async def delete(self, session_id: str) -> None:
        """Remove a session explicitly (e.g. after completion)."""
        key = self._key(session_id)
        await self._cache.delete(key)
        logger.info("Session deleted: %s", session_id)

    async def extend_ttl(self, session_id: str) -> None:
        """Reset the TTL on an existing session (keep-alive)."""
        key = self._key(session_id)
        raw = await self._cache.get(key)
        if raw:
            await self._cache.set(key, raw, ttl=self._ttl)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _key(session_id: str) -> str:
        return f"{_KEY_PREFIX}:{session_id}"
