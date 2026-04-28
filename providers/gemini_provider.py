import os
import instructor
from google import genai
from typing import Any, Dict, List, Optional
from providers.base_provider import BaseProvider

class GeminiProvider(BaseProvider):
    def __init__(self, api_key: Optional[str] = None):
        key = api_key or os.environ.get("GEMINI_API_KEY")
        if not key:
            raise ValueError("GEMINI_API_KEY not found")
            
        self._raw_client = genai.Client(api_key=key)
        self._instructor_client = instructor.from_genai(
            client=self._raw_client,
            mode=instructor.Mode.GENAI_STRUCTURED_OUTPUTS,
        )

    async def generate_response(self, messages: List[Dict[str, str]], model: str = "gemini-2.5-flash", **kwargs) -> str:
        # Convert standard OpenAI/Claude format to Gemini if necessary
        contents = "\n".join([f"{m['role']}: {m['content']}" for m in messages])
        response = self._raw_client.models.generate_content(
            model=model,
            contents=contents,
        )
        return response.text

    async def get_structured_output(self, messages: List[Dict[str, str]], response_model: Any, model: str = "gemini-2.5-flash", **kwargs) -> Any:
        # Instructor handles the structured output logic
        response = self._instructor_client.chat.completions.create(
            messages=messages,
            response_model=response_model,
            model=model,
        )
        return response
