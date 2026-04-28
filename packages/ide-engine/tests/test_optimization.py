import pytest
import yaml

from engine.optimization.cost_tracker import CostTracker
from engine.optimization.prompt_cache import PromptCache
from engine.optimization.token_optimizer import TokenOptimizer
from engine.providers.base_provider import BaseProvider
from engine.providers.router import ProviderRouter


class DummyProvider(BaseProvider):
    async def generate_response(self, messages, model="dummy", **kwargs):
        return "dummy"

    async def get_structured_output(self, messages, response_model, model="dummy", **kwargs):
        return "dummy_structured"


def test_token_pruning():
    long_output = "\n".join([f"Line {i}" for i in range(200)])
    pruned = TokenOptimizer.prune_terminal_output(long_output, max_lines=10)

    assert "Line 0" in pruned
    assert "Line 4" in pruned
    assert "Line 199" in pruned
    assert "lines omitted" in pruned
    assert len(pruned.splitlines()) < 200


def test_cost_tracker():
    tracker = CostTracker()
    tracker.track("gemini-2.5-flash", input_tokens=1000000, output_tokens=1000000)
    summary = tracker.get_summary()
    assert summary["total_cost_usd"] == 0.375  # 0.075 + 0.30


def test_router():
    router = ProviderRouter()
    gemini = DummyProvider()
    anthropic = DummyProvider()

    router.register_provider("gemini", gemini)
    router.register_provider("anthropic", anthropic)

    assert router.route("high") == anthropic
    assert router.route("medium") == gemini


def test_profile_load():
    import os

    path = os.path.join(os.path.dirname(__file__), "../profiles/socroot.yaml")
    with open(path, "r") as f:
        config = yaml.safe_load(f)
    assert config["project"]["name"] == "IDE Agentic Engine"
    assert config["routing"]["default_provider"] == "gemini"
