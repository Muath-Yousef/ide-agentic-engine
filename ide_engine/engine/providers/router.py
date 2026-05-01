from typing import Any, Dict, List

from engine.providers.base_provider import BaseProvider


class ProviderRouter:
    """
    Intelligently routes tasks to the most suitable LLM based on task complexity
    and cost requirements.
    """

    def __init__(self, default_provider: str = "groq"):
        self.providers: Dict[str, BaseProvider] = {}
        self.default_provider = default_provider

    def register_provider(self, name: str, provider: BaseProvider):
        self.providers[name] = provider

    def route(self, task_complexity: str = "medium") -> BaseProvider:
        """
        Routing logic:
        1. Try the default provider first if it's valid for the complexity.
        2. Fallback to others based on complexity.
        """

        def is_valid(name):
            provider = self.providers.get(name)
            if not provider or getattr(provider, "_instructor_client", None) is None:
                return False
            
            if hasattr(provider, "key_pool") and provider.key_pool:
                key = provider.key_pool.get_key(name)
                return key is not None
            return True

        # 1. Try Default Provider first
        if is_valid(self.default_provider):
            return self.providers[self.default_provider]

        # 2. Complexity-based fallbacks
        if task_complexity == "high":
            for name in ["anthropic", "openai", "gemini"]:
                if is_valid(name):
                    return self.providers[name]
        else:
            for name in ["gemini", "openai", "groq"]:
                if is_valid(name):
                    return self.providers[name]

        # 3. Last resort fallback
        if not self.providers:
            raise ValueError("No providers registered with ProviderRouter")

        for name, provider in self.providers.items():
            if is_valid(name):
                return provider

        return next(iter(self.providers.values()))
