import os
import instructor
from google import genai
from google.genai.errors import ClientError
from typing import Any, Dict, List, Optional
from providers.base_provider import BaseProvider
from gateway.key_pool import APIKeyPool

class GeminiProvider(BaseProvider):
    def __init__(self, api_key: Optional[str] = None, key_pool: Optional[APIKeyPool] = None):
        self.key_pool = key_pool
        self._initialize_client(fallback_key=api_key)

    def _initialize_client(self, fallback_key: Optional[str] = None):
        key = fallback_key
        if not key and self.key_pool:
            key = self.key_pool.get_key("gemini")
        
        if not key:
            key = os.environ.get("GEMINI_API_KEY")

        if not key:
            raise ValueError("GEMINI_API_KEY not found in Key Pool or environment")

        self.current_key = key
        self._raw_client = genai.Client(api_key=key)
        self._instructor_client = instructor.from_genai(
            client=self._raw_client,
            mode=instructor.Mode.GENAI_STRUCTURED_OUTPUTS,
        )

    async def generate_response(self, messages: List[Dict[str, str]], model: str = "gemini-2.5-flash", **kwargs) -> str:
        max_retries = 3
        for attempt in range(max_retries):
            try:
                contents = "\n".join([f"{m['role']}: {m['content']}" for m in messages])
                response = self._raw_client.models.generate_content(
                    model=model,
                    contents=contents,
                )
                return response.text
            except ClientError as e:
                error_str = str(e)
                if ("429" in error_str or "403" in error_str) and self.key_pool:
                    is_rate_limit = "429" in error_str
                    self.key_pool.mark_exhausted("gemini", self.current_key, is_rate_limit=is_rate_limit)
                    self._initialize_client()
                else:
                    raise e
        raise RuntimeError("All available keys exhausted or max retries reached.")

    async def get_structured_output(self, messages: List[Dict[str, str]], response_model: Any, model: str = "gemini-2.5-flash", **kwargs) -> Any:
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self._instructor_client.chat.completions.create(
                    messages=messages,
                    response_model=response_model,
                    model=model,
                )
                return response
            except ClientError as e:
                error_str = str(e)
                if ("429" in error_str or "403" in error_str) and self.key_pool:
                    is_rate_limit = "429" in error_str
                    self.key_pool.mark_exhausted("gemini", self.current_key, is_rate_limit=is_rate_limit)
                    self._initialize_client()
                else:
                    raise e
        raise RuntimeError("All available keys exhausted or max retries reached.")
