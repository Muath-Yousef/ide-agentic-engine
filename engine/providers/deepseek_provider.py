import os
from typing import Any, Dict, List, Optional

import instructor
from openai import AsyncOpenAI

from core.key_pool import APIKeyPool
from engine.providers.base_provider import BaseProvider


class DeepSeekProvider(BaseProvider):
    def __init__(self, api_key: Optional[str] = None, key_pool: Optional[APIKeyPool] = None):
        self.key_pool = key_pool
        self._initialize_client(fallback_key=api_key)

    def _initialize_client(self, fallback_key: Optional[str] = None):
        key = fallback_key
        if not key and self.key_pool:
            key = self.key_pool.get_key("deepseek")

        if not key:
            key = os.environ.get("DEEPSEEK_API_KEY")

        if not key:
            import logging

            logging.getLogger(__name__).warning("DEEPSEEK_API_KEY not available yet.")
            self.current_key = None
            self._raw_client = None
            self._instructor_client = None
            return

        self.current_key = key
        self._raw_client = AsyncOpenAI(api_key=key, base_url="https://api.deepseek.com")
        self._instructor_client = instructor.from_openai(
            client=self._raw_client,
            mode=instructor.Mode.TOOLS,
        )

    def _ensure_client(self):
        if self._raw_client is None:
            self._initialize_client()
        if self._raw_client is None:
            raise RuntimeError("DeepSeek provider has no active API key.")

    async def generate_response(
        self, messages: List[Dict[str, str]], model: str = "deepseek-chat", **kwargs
    ) -> str:
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self._ensure_client()
                response = await self._raw_client.chat.completions.create(
                    model=model, messages=messages, **kwargs
                )
                return response.choices[0].message.content or ""
            except Exception as e:
                error_str = str(e).lower()
                if ("429" in error_str or "rate limit" in error_str) and self.key_pool:
                    self.key_pool.mark_exhausted("deepseek", self.current_key, is_rate_limit=True)
                    self._initialize_client()
                else:
                    raise e
        raise RuntimeError("All DeepSeek keys exhausted.")

    async def get_structured_output(
        self,
        messages: List[Dict[str, str]],
        response_model: Any,
        model: str = "deepseek-chat",
        **kwargs,
    ) -> Any:
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self._ensure_client()
                response = await self._instructor_client.chat.completions.create(
                    messages=messages, response_model=response_model, model=model, **kwargs
                )
                return response
            except Exception as e:
                error_str = str(e).lower()
                if ("429" in error_str or "rate limit" in error_str) and self.key_pool:
                    self.key_pool.mark_exhausted("deepseek", self.current_key, is_rate_limit=True)
                    self._initialize_client()
                else:
                    raise e
        raise RuntimeError("All DeepSeek keys exhausted.")
