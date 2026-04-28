from typing import Dict, Any, List
from providers.base_provider import BaseProvider

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
        - high complexity -> anthropic (claude-3-5-sonnet)
        - medium/low complexity -> gemini (gemini-2.5-flash)
        """
        if task_complexity == "high" and "anthropic" in self.providers:
            return self.providers["anthropic"]
        elif task_complexity in ["low", "medium"] and "gemini" in self.providers:
            return self.providers["gemini"]
            
        # Fallback
        if self.default_provider in self.providers:
            return self.providers[self.default_provider]
            
        # Last resort
        if not self.providers:
            raise ValueError("No providers registered with ProviderRouter")
            
        return next(iter(self.providers.values()))
