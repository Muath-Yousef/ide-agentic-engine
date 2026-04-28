from typing import Any, Dict, List

from engine.providers.base_provider import BaseProvider


class ProviderRouter:
    """
    Intelligently routes tasks to the most suitable LLM based on task complexity
    and cost requirements.
    """

    def __init__(self, default_provider: str = "gemini"):
        self.providers: Dict[str, BaseProvider] = {}
        self.default_provider = default_provider

    def register_provider(self, name: str, provider: BaseProvider):
        self.providers[name] = provider

    def route(self, task_complexity: str = "medium") -> BaseProvider:
        """
        Routing logic:
        - high complexity -> anthropic or openai
        - medium/low complexity -> gemini
        """

        def is_valid(name):
            return (
                name in self.providers
                and getattr(self.providers[name], "_instructor_client", None) is not None
            )

        if task_complexity == "high":
            if is_valid("anthropic"):
                return self.providers["anthropic"]
            if is_valid("openai"):
                return self.providers["openai"]

        if task_complexity in ["low", "medium"]:
            if is_valid("gemini"):
                return self.providers["gemini"]

        # Fallback to whatever is available and functional
        for name in ["openai", "gemini", "anthropic"]:
            if is_valid(name):
                return self.providers[name]

        # Last resort fallback if nothing is fully initialized
        if not self.providers:
            raise ValueError("No providers registered with ProviderRouter")

        return next(iter(self.providers.values()))
