import json
import os
import re
from typing import Any, Dict, List, Optional, Type

from google import genai
from google.genai import types
from google.genai.errors import ClientError
from pydantic import BaseModel

from core.key_pool import APIKeyPool
from engine.providers.base_provider import BaseProvider

# Gemini supports these roles only
_ROLE_MAP = {"system": "user", "assistant": "model", "model": "model", "user": "user"}


class GeminiProvider(BaseProvider):
    def __init__(self, api_key: Optional[str] = None, key_pool: Optional[APIKeyPool] = None):
        self.key_pool = key_pool
        self._instructor_client = None  # Not used, kept for router compatibility check
        self._initialize_client(fallback_key=api_key)

    def _initialize_client(self, fallback_key: Optional[str] = None):
        key = fallback_key
        if not key and self.key_pool:
            key = self.key_pool.get_key("gemini")

        if not key:
            key = os.environ.get("GEMINI_API_KEY")

        if not key:
            import logging

            logging.getLogger(__name__).warning(
                "GEMINI_API_KEY not available yet (keys may be in cooldown). "
                "Provider created in deferred mode — will retry on next call."
            )
            self.current_key = None
            self._raw_client = None
            self._instructor_client = None
            return

        self.current_key = key
        self._raw_client = genai.Client(api_key=key)
        self._instructor_client = True  # Mark as configured for router's is_valid check

    def _build_contents(self, messages: List[Dict[str, str]]):
        """Convert messages list to Gemini contents, merging system prompt into first user turn."""
        contents = []
        system_parts = []

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "system":
                system_parts.append(content)
            else:
                gemini_role = _ROLE_MAP.get(role, "user")
                contents.append(types.Content(role=gemini_role, parts=[types.Part(text=content)]))

        # Prepend system prompt to first user turn if any
        if system_parts and contents:
            system_text = "\n\n".join(system_parts)
            first = contents[0]
            merged_text = system_text + "\n\n---\n\n" + first.parts[0].text
            contents[0] = types.Content(role="user", parts=[types.Part(text=merged_text)])
        elif system_parts:
            # Only system parts — make it a user turn
            contents.append(
                types.Content(role="user", parts=[types.Part(text="\n\n".join(system_parts))])
            )

        return contents

    def _ensure_client(self):
        """Re-attempt initialization if provider is in deferred mode."""
        if self._raw_client is None:
            self._initialize_client()
        if self._raw_client is None:
            raise RuntimeError(
                "Gemini provider has no active API key. "
                "All keys may be in cooldown or exhausted."
            )

    async def generate_response(
        self, messages: List[Dict[str, str]], model: str = "gemini-2.0-flash", **kwargs
    ) -> str:
        self._ensure_client()
        max_retries = 3
        for attempt in range(max_retries):
            try:
                contents = self._build_contents(messages)
                response = self._raw_client.models.generate_content(
                    model=model,
                    contents=contents,
                )
                return response.text or ""
            except ClientError as e:
                error_str = str(e)
                if ("429" in error_str or "403" in error_str) and self.key_pool:
                    is_rate_limit = "429" in error_str
                    self.key_pool.mark_exhausted(
                        "gemini", self.current_key, is_rate_limit=is_rate_limit
                    )
                    self._initialize_client()
                else:
                    raise e
        raise RuntimeError("All available keys exhausted or max retries reached.")

    async def get_structured_output(
        self,
        messages: List[Dict[str, str]],
        response_model: Type[BaseModel],
        model: str = "gemini-2.0-flash",
        **kwargs,
    ) -> Any:
        """
        Use raw Gemini API with JSON prompt injection to get structured output.
        Bypasses instructor to avoid schema/role compatibility issues.
        """
        self._ensure_client()
        schema = response_model.model_json_schema()
        # Remove additionalProperties fields Gemini rejects
        _strip_additional_properties(schema)
        schema_str = json.dumps(schema, indent=2)

        # Inject JSON instruction into the messages
        json_instruction = (
            f"\n\nYou MUST respond with a single, valid JSON object that strictly follows this schema:\n"
            f"```json\n{schema_str}\n```\n"
            "Do not include any text before or after the JSON object. Only output the JSON."
        )

        # Append instruction to last user message
        augmented_messages = list(messages)
        for i in range(len(augmented_messages) - 1, -1, -1):
            if augmented_messages[i].get("role") in ("user", "system"):
                augmented_messages[i] = {
                    **augmented_messages[i],
                    "content": augmented_messages[i]["content"] + json_instruction,
                }
                break

        max_retries = 3
        for attempt in range(max_retries):
            try:
                self._ensure_client()
                contents = self._build_contents(augmented_messages)
                response = self._raw_client.models.generate_content(
                    model=model,
                    contents=contents,
                    config=types.GenerateContentConfig(response_mime_type="application/json"),
                )
                raw_text = response.text or ""
                # Strip markdown fences if present
                raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text.strip())
                raw_text = re.sub(r"\s*```$", "", raw_text.strip())

                parsed = json.loads(raw_text)
                return response_model.model_validate(parsed)
            except ClientError as e:
                error_str = str(e)
                if ("429" in error_str or "403" in error_str) and self.key_pool:
                    is_rate_limit = "429" in error_str
                    self.key_pool.mark_exhausted(
                        "gemini", self.current_key, is_rate_limit=is_rate_limit
                    )
                    self._initialize_client()
                else:
                    raise e
            except (json.JSONDecodeError, Exception) as e:
                if attempt == max_retries - 1:
                    raise RuntimeError(
                        f"Failed to parse structured output after {max_retries} attempts: {e}"
                    ) from e
        raise RuntimeError("All available keys exhausted or max retries reached.")


def _strip_additional_properties(schema: dict):
    """Recursively remove 'additionalProperties' from JSON schema to satisfy Gemini."""
    schema.pop("additionalProperties", None)
    for key, value in schema.items():
        if isinstance(value, dict):
            _strip_additional_properties(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    _strip_additional_properties(item)
