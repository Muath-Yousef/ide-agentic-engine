import os
from typing import Any, Dict, List, Optional

import instructor
from anthropic import AsyncAnthropic

from engine.providers.base_provider import BaseProvider


class AnthropicProvider(BaseProvider):
    def __init__(self, api_key: Optional[str] = None, key_pool: Optional[Any] = None):
        self.key_pool = key_pool
        self._initialize_client(fallback_key=api_key)

    def _initialize_client(self, fallback_key: Optional[str] = None):
        key = fallback_key
        if not key and self.key_pool:
            key = self.key_pool.get_key("anthropic")

        if not key:
            key = os.environ.get("ANTHROPIC_API_KEY")

        if not key:
            # We don't raise here to allow the engine to start even if one provider is missing keys
            # But we will log a warning
            import logging

            logging.getLogger(__name__).warning("ANTHROPIC_API_KEY not found")
            self._raw_client = None
            self._instructor_client = None
            return

        self.current_key = key
        self._raw_client = AsyncAnthropic(api_key=key)
        self._instructor_client = instructor.from_anthropic(self._raw_client)

    @property
    def is_configured(self) -> bool:
        return self._instructor_client is not None

    async def generate_response(
        self, messages: List[Dict[str, str]], model: str = "claude-3-5-sonnet-20241022", **kwargs
    ) -> str:
        system_prompt = next((m["content"] for m in messages if m["role"] == "system"), "")
        filtered_messages = [m for m in messages if m["role"] != "system"]

        response = await self._raw_client.messages.create(
            model=model,
            messages=filtered_messages,
            system=system_prompt,
            max_tokens=kwargs.get("max_tokens", 4096),
        )
        return response.content[0].text

    async def get_structured_output(
        self,
        messages: List[Dict[str, str]],
        response_model: Any,
        model: str = "claude-3-5-sonnet-20241022",
        **kwargs,
    ) -> Any:
        system_prompt = next((m["content"] for m in messages if m["role"] == "system"), "")
        filtered_messages = [m for m in messages if m["role"] != "system"]

        response = await self._instructor_client.messages.create(
            model=model,
            messages=filtered_messages,
            system=system_prompt,
            max_tokens=kwargs.get("max_tokens", 4096),
            response_model=response_model,
        )
        return response
