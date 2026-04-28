from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

class BaseProvider(ABC):
    """
    Abstract Base Class for LLM Providers.
    Ensures all providers implement the same interface for the orchestrator.
    """
    @abstractmethod
    async def generate_response(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Generate a standard text response from the LLM."""
        pass
        
    @abstractmethod
    async def get_structured_output(self, messages: List[Dict[str, str]], response_model: Any, **kwargs) -> Any:
        """Force the LLM to return a structured Pydantic object."""
        pass
