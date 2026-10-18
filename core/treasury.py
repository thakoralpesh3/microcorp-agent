"""
MicroCorp AI - Treasury & ROI Accounting Module
Tracks estimated deliverable value, real LLM token costs, and company balance sheet.
"""

from typing import Dict, Any, List
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.database import record_treasury_event, get_treasury_summary

# Benchmark estimated values for autonomous deliverables
DELIVERABLE_VALUE_BENCHMARKS = {
    "digital_product": 19.0,      # Average Gumroad / itch digital download sale price
    "prompt_pack": 15.0,          # Curated production prompt pack
    "newsletter_edition": 25.0,   # Sponsorship/subscriber value per edition
    "affiliate_guide": 45.0,      # Lifetime affiliate commission value
    "freelance_proposal": 250.0,  # Expected project fee for tailored proposal
    "freelance_turnkey": 280.0,   # Completed turnkey client delivery fee
    "lead_dataset": 35.0          # B2B verified niche dataset
}

# Gemini Token Cost benchmarks (per million tokens in USD)
# Flash-lite tier: ~$0.075 / 1M input, ~$0.30 / 1M output
COST_PER_1M_INPUT = 0.075
COST_PER_1M_OUTPUT = 0.30

class Treasury:
    @staticmethod
    def calculate_token_cost(prompt_tokens: int, completion_tokens: int) -> float:
        input_cost = (prompt_tokens / 1_000_000.0) * COST_PER_1M_INPUT
        output_cost = (completion_tokens / 1_000_000.0) * COST_PER_1M_OUTPUT
        return round(input_cost + output_cost, 5)

    @staticmethod
    def log_deliverable(category: str, title: str, deliverable_path: str, prompt_tokens: int = 1500, completion_tokens: int = 2500) -> Dict[str, Any]:
        """Logs a completed deliverable to the company treasury ledger."""
        est_val = DELIVERABLE_VALUE_BENCHMARKS.get(category, 20.0)
        token_cost = Treasury.calculate_token_cost(prompt_tokens, completion_tokens)
        
        record_treasury_event(
            category=category,
            title=title,
            amount_est_usd=est_val,
            token_cost_usd=token_cost,
            deliverable_path=deliverable_path,
            status="ready_for_review"
        )
        return {
            "title": title,
            "estimated_value_usd": est_val,
            "token_cost_usd": token_cost,
            "roi_ratio": round(est_val / max(token_cost, 0.0001), 1)
        }

    @staticmethod
    def log_transaction(category: str, description: str, amount: float, is_revenue: bool = True, deliverable_path: str = "") -> Dict[str, Any]:
        """Logs custom revenue or financial transactions directly into the ledger."""
        token_cost = 0.005 if is_revenue else 0.0
        record_treasury_event(
            category=category,
            title=description,
            amount_est_usd=amount,
            token_cost_usd=token_cost,
            deliverable_path=deliverable_path,
            status="completed"
        )
        return {
            "title": description,
            "amount": amount,
            "is_revenue": is_revenue
        }

    @staticmethod
    def get_financial_summary() -> Dict[str, Any]:
        return get_treasury_summary()

treasury = Treasury()
