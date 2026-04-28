from typing import Dict

class CostTracker:
    """
    Tracks token usage per session and estimates cost.
    """
    PRICING = {
        "claude-3-5-sonnet-20241022": {"input": 3.0 / 1_000_000, "output": 15.0 / 1_000_000},
        "gemini-2.5-flash": {"input": 0.075 / 1_000_000, "output": 0.30 / 1_000_000},
        "deepseek-coder": {"input": 0.14 / 1_000_000, "output": 0.28 / 1_000_000},
        "deepseek-chat": {"input": 0.14 / 1_000_000, "output": 0.28 / 1_000_000},
    }

    def __init__(self):
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost = 0.0
        self.usage_by_model: Dict[str, Dict[str, int]] = {}

    def track(self, model: str, input_tokens: int, output_tokens: int):
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        
        if model not in self.usage_by_model:
            self.usage_by_model[model] = {"input": 0, "output": 0}
            
        self.usage_by_model[model]["input"] += input_tokens
        self.usage_by_model[model]["output"] += output_tokens
        
        rates = self.PRICING.get(model, {"input": 0.0, "output": 0.0})
        cost = (input_tokens * rates["input"]) + (output_tokens * rates["output"])
        self.total_cost += cost

    def get_summary(self) -> Dict[str, float]:
        return {
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_cost_usd": round(self.total_cost, 4),
            "usage_by_model": self.usage_by_model
        }
