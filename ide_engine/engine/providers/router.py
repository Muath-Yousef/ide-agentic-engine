from typing import Any, Callable, Dict, List

from engine.providers.base_provider import BaseProvider


class ProviderRouter:
    """
    Routes LLM tasks to the best available provider with automatic runtime fallback.
    - route()               → returns the best provider (pre-call selection)
    - route_with_fallback() → executes the call and retries on 401/429 automatically
    """

    def __init__(self, default_provider: str = "groq"):
        self.providers: Dict[str, BaseProvider] = {}
        self.default_provider = default_provider

    def register_provider(self, name: str, provider: BaseProvider):
        self.providers[name] = provider

    def _is_valid(self, name: str) -> bool:
        """Check if a provider has a live client and an available key."""
        provider = self.providers.get(name)
        if not provider or getattr(provider, "_instructor_client", None) is None:
            return False
        if hasattr(provider, "key_pool") and provider.key_pool:
            return provider.key_pool.get_key(name) is not None
        return True

    def get_fallback_order(self, task_complexity: str = "medium") -> List[str]:
        """Returns the ordered list of provider names to try, deduped."""
        if task_complexity == "high":
            order = [self.default_provider, "anthropic", "openai", "gemini", "groq"]
        else:
            order = [self.default_provider, "groq", "gemini", "openai", "anthropic"]

        seen: set = set()
        result: List[str] = []
        for name in order:
            if name not in seen and name in self.providers:
                seen.add(name)
                result.append(name)
        return result

    def route(self, task_complexity: str = "medium") -> BaseProvider:
        """
        Select the best provider at call time (pre-flight check only).
        For runtime error handling, prefer route_with_fallback().
        """
        # 1. Default provider
        if self._is_valid(self.default_provider):
            return self.providers[self.default_provider]

        # 2. Complexity-based order
        for name in self.get_fallback_order(task_complexity):
            if self._is_valid(name):
                return self.providers[name]

        # 3. Last resort — return any registered provider
        if not self.providers:
            raise ValueError("No providers registered with ProviderRouter")
        return next(iter(self.providers.values()))

    async def route_with_fallback(self, call_fn: Callable, task_complexity: str = "medium"):
        """
        Execute call_fn(provider) with automatic failover on 401 / 429 errors.

        Example:
            result = await router.route_with_fallback(
                lambda p: p.chat(messages=msgs, response_model=MyModel)
            )
        """
        import logging
        logger = logging.getLogger(__name__)

        # HTTP status codes that mean "try someone else"
        RETRYABLE = {"401", "429", "RESOURCE_EXHAUSTED", "Unauthorized"}

        providers_to_try = self.get_fallback_order(task_complexity)
        last_exc: Exception | None = None

        for name in providers_to_try:
            provider = self.providers.get(name)
            if not provider:
                continue
            try:
                logger.info(f"🔄 Trying provider: {name}")
                result = await call_fn(provider)
                logger.info(f"✅ Provider '{name}' succeeded.")
                return result
            except Exception as exc:
                exc_str = str(exc)
                if any(code in exc_str for code in RETRYABLE):
                    logger.warning(f"⚠️  Provider '{name}' rejected ({exc_str[:100]}). Trying next...")
                    last_exc = exc
                    continue
                # Non-retryable (bad schema, network timeout, etc.) — re-raise immediately
                raise

        raise RuntimeError(
            f"All providers exhausted after trying {providers_to_try}. "
            f"Last error: {last_exc}"
        ) from last_exc
