import logging
from typing import Any, Optional, Type, TypeVar

from pydantic import BaseModel

from engine.optimization.prompt_cache import PromptCache
from engine.providers.router import ProviderRouter

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class LLMManager:
    """
    High-level orchestrator for LLM calls.
    Handles routing, structured output (via Instructor), and caching.
    """

    def __init__(self):
        self.router = ProviderRouter()
        self.cache = PromptCache()
        # Initialize providers if not already done
        self._setup_default_providers()

    def _setup_default_providers(self):
        # This would typically be driven by config/profiles
        from core.key_pool import APIKeyPool
        from engine.providers.anthropic_provider import AnthropicProvider
        from engine.providers.gemini_provider import GeminiProvider

        key_pool = APIKeyPool()
        self.router.register_provider("gemini", GeminiProvider(key_pool=key_pool))
        self.router.register_provider("anthropic", AnthropicProvider(key_pool=key_pool))

    async def call_structured(
        self,
        task_type: str,
        user_prompt: str,
        response_model: Type[T],
        system: Optional[str] = None,
        use_result_cache: bool = True,
        use_prompt_cache: bool = False,
        **kwargs,
    ) -> T:
        """
        Calls an LLM and returns a validated Pydantic model.
        """
        # 1. Check Result Cache
        if use_result_cache:
            cached = self.cache.get_structured(user_prompt, response_model)
            if cached:
                logger.info(f"Cache hit for task: {task_type}")
                return cached

        # 2. Route to Provider
        # For now, simple routing based on task_type or default
        priority = "high" if task_type in ["compliance", "report_gen"] else "medium"
        provider = self.router.route(priority)

        # 3. Execute with structured output
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": user_prompt})

        result = await provider.get_structured_output(
            messages=messages, response_model=response_model, **kwargs
        )

        # 4. Save to Cache
        if use_result_cache:
            self.cache.set_structured(user_prompt, result)

        return result
