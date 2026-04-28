import os
import instructor
from anthropic import AsyncAnthropic
from typing import Any, Dict, List, Optional
from providers.base_provider import BaseProvider

class AnthropicProvider(BaseProvider):
    def __init__(self, api_key: Optional[str] = None):
        key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise ValueError("ANTHROPIC_API_KEY not found")
        self._raw_client = AsyncAnthropic(api_key=key)
        self._instructor_client = instructor.from_anthropic(self._raw_client)

    async def generate_response(self, messages: List[Dict[str, str]], model: str = "claude-3-5-sonnet-20241022", **kwargs) -> str:
        system_prompt = next((m["content"] for m in messages if m["role"] == "system"), "")
        filtered_messages = [m for m in messages if m["role"] != "system"]
        
        response = await self._raw_client.messages.create(
            model=model,
            messages=filtered_messages,
            system=system_prompt,
            max_tokens=kwargs.get("max_tokens", 4096)
        )
        return response.content[0].text

    async def get_structured_output(self, messages: List[Dict[str, str]], response_model: Any, model: str = "claude-3-5-sonnet-20241022", **kwargs) -> Any:
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
