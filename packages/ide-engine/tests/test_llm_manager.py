from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import BaseModel

from engine.llm_manager import LLMManager


class MockResponseModel(BaseModel):
    answer: str


@pytest.mark.asyncio
async def test_llm_manager_call_structured_cache_hit():
    with patch("core.key_pool.APIKeyPool") as mock_pool:
        mock_pool.return_value.get_key.return_value = "dummy_key"
        manager = LLMManager()
        manager.cache = MagicMock()

        mock_result = MockResponseModel(answer="cached_answer")
        manager.cache.get_structured.return_value = mock_result

        result = await manager.call_structured(
            task_type="test", user_prompt="prompt", response_model=MockResponseModel
        )

        assert result.answer == "cached_answer"
        manager.cache.get_structured.assert_called_once()


@pytest.mark.asyncio
async def test_llm_manager_call_structured_routing():
    with patch("core.key_pool.APIKeyPool") as mock_pool:
        mock_pool.return_value.get_key.return_value = "dummy_key"
        with patch("engine.providers.router.ProviderRouter.route") as mock_route:
            mock_provider = MagicMock()
            mock_provider.get_structured_output = AsyncMock(
                return_value=MockResponseModel(answer="real_answer")
            )
            mock_route.return_value = mock_provider

            manager = LLMManager()
            manager.cache = MagicMock()
            manager.cache.get_structured.return_value = None

            result = await manager.call_structured(
                task_type="compliance", user_prompt="heavy task", response_model=MockResponseModel
            )

            assert result.answer == "real_answer"
            # Compliance task should route with high complexity
            mock_route.assert_called_with("high")
            manager.cache.set_structured.assert_called_once()
