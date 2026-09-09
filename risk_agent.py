from __future__ import annotations

from typing import Any, Dict

from base_agent import BaseAgent


class RiskAgent(BaseAgent):
    SYSTEM_PROMPT = "Risk specialist: score loan applications and flag risky clients."

    def perform_task(self, payload: Dict[str, Any]) -> Any:
        application = payload.get("application", {})
        score = 0.5
        amount = application.get("amount") or 0
        if amount > 50000:
            score = 0.9
        verdict = "high" if score > 0.8 else "low"
        return {"score": score, "verdict": verdict, "amount": amount}
