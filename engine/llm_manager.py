import os
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Type, TypeVar

import instructor
import openai
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


# ============================================================================
# Token Optimization & Caching Scaffolding
# ============================================================================
class TokenOptimizer:
    """
    Advanced Token Optimizer for IDE Context.
    Handles semantic compression, truncating middle of large files,
    and prioritizing recent/relevant code chunks.
    """

    def optimize(self, messages: List[Dict[str, str]], max_tokens: int) -> List[Dict[str, str]]:
        # Placeholder for advanced token compression logic
        # Example: removing redundant tool outputs if context is too large
        return messages


class PromptCache:
    """
    In-memory or persistent cache to save API calls for identical prompts
    (e.g., repeating the same AST parsing request).
    """

    def __init__(self):
        self._cache = {}

    def get(self, key: str) -> Optional[Any]:
        return self._cache.get(key)

    def set(self, key: str, value: Any, ttl: int):
        self._cache[key] = {"value": value, "expires": time.time() + ttl}


def get_cache() -> PromptCache:
    return PromptCache()


# ============================================================================
# Model Routing Configuration
# ============================================================================
@dataclass
class ModelConfig:
    model: str
    max_tokens: int
    cache_ttl: int
    temperature: float = 0.2


# Specialized routes for different IDE agent tasks
ROUTING_TABLE: dict[str, ModelConfig] = {
    "triage": ModelConfig(model="deepseek-chat", max_tokens=256, cache_ttl=300, temperature=0.1),
    "simple_qa": ModelConfig(
        model="deepseek-chat", max_tokens=512, cache_ttl=86_400, temperature=0.3
    ),
    "code_generation": ModelConfig(
        model="deepseek-coder", max_tokens=8_192, cache_ttl=3_600, temperature=0.2
    ),
    "code_review": ModelConfig(
        model="deepseek-coder", max_tokens=4_096, cache_ttl=3_600, temperature=0.1
    ),
    "terminal_planning": ModelConfig(
        model="deepseek-chat", max_tokens=1_024, cache_ttl=0, temperature=0.1
    ),
}


# ============================================================================
# Core IDE LLM Manager
# ============================================================================
class LLMManager:
    """
    The Brain of the IDE Agentic Engine.
    Handles dynamic routing, token optimization, structured outputs (Instructor),
    and robust error handling specific to coding agent workflows.
    """

    def __init__(
        self, optimizer: Optional[TokenOptimizer] = None, spec_path: str = "PROJECT_SPEC.md"
    ) -> None:
        api_key = os.environ.get("DEEP_SEEK_API_KEY", "dummy-key-for-now")

        # Initialize standard OpenAI client pointed at DeepSeek
        self._raw_client = openai.OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

        # Wrap with Instructor for guaranteed structured Pydantic outputs
        self._instructor_client = instructor.from_openai(self._raw_client)

        self._cache = get_cache()
        self._optimizer = optimizer or TokenOptimizer()
        self._spec_path = spec_path

    def get_structured_output(
        self,
        messages: List[Dict[str, str]],
        response_model: Type[T],
        route: str = "code_generation",
    ) -> T:
        """
        Forces the LLM to reply exactly in the shape of the provided Pydantic model.
        Crucial for IDE tool calling and state management.
        """
        config = ROUTING_TABLE.get(route, ROUTING_TABLE["code_generation"])

        # Optimize context window before sending
        optimized_messages = self._optimizer.optimize(messages, config.max_tokens)

        # Execute through Instructor
        response = self._instructor_client.chat.completions.create(
            model=config.model,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            messages=optimized_messages,
            response_model=response_model,
        )
        return response

    def generate_stream(self, messages: List[Dict[str, str]], route: str = "code_generation"):
        """
        Streams the response back. Vital for IDE UI responsiveness
        so the user sees code being typed in real-time.
        """
        config = ROUTING_TABLE.get(route, ROUTING_TABLE["code_generation"])
        optimized_messages = self._optimizer.optimize(messages, config.max_tokens)

        response = self._raw_client.chat.completions.create(
            model=config.model,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            messages=optimized_messages,
            stream=True,
        )

        for chunk in response:
            if chunk.choices[0].delta.content is not None:
                yield chunk.choices[0].delta.content
