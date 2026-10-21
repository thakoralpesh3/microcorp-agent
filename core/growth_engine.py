"""
MicroCorp AI - Autonomous Self-Growth & Enterprise Evolution Engine
Enables the company to evaluate market demand, dynamically found new departments,
scale asset pricing, level up enterprise capabilities, and reinvest profits.
"""

import os
import sys
import json
import time
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import DATA_DIR, USD_TO_INR_RATE
from core.database import (
    get_connection, get_all_departments, create_department, 
    update_department_subagent_count, record_metrics
)
from core.treasury import treasury

logger = logging.getLogger("MicroCorp.GrowthEngine")
GROWTH_STATE_FILE = DATA_DIR / "growth_evolution_state.json"

TIER_CONFIG = {
    1: {
        "name": "Seed Startup",
        "min_revenue_usd": 0.0,
        "max_subagents_per_dept": 2,
        "base_product_price_usd": 19.0,
        "badge": "🌱 Tier 1: Seed Startup"
    },
    2: {
        "name": "Scaled Boutique Agency",
        "min_revenue_usd": 500.0,
        "max_subagents_per_dept": 4,
        "base_product_price_usd": 39.0,
        "badge": "🚀 Tier 2: Scaled Boutique"
    },
    3: {
        "name": "Multi-Domain Enterprise",
        "min_revenue_usd": 2500.0,
        "max_subagents_per_dept": 6,
        "base_product_price_usd": 69.0,
        "badge": "🏢 Tier 3: Multi-Domain Enterprise"
    },
    4: {
        "name": "Autonomous Conglomerate",
        "min_revenue_usd": 10000.0,
        "max_subagents_per_dept": 8,
        "base_product_price_usd": 99.0,
        "badge": "👑 Tier 4: Autonomous Conglomerate"
    }
}

EMERGING_DOMAINS_CATALOG = [
    {
        "domain": "agentic_ai",
        "name": "Autonomous AI Agent Lab",
        "head_title": "Chief Agent Architect",
        "description": "Engineers production-grade LangChain/LangGraph and autonomous multi-agent toolkits.",
        "icon": "fa-solid fa-robot",
        "base_price_usd": 49.0
    },
    {
        "domain": "cloud_devops",
        "name": "Cloud Architecture & DevOps Fleet",
        "head_title": "Principal Systems Architect",
        "description": "Manufactures Docker compose scaffolds, Kubernetes configs, and CI/CD pipelines.",
        "icon": "fa-solid fa-server",
        "base_price_usd": 39.0
    },
    {
        "domain": "data_scraping",
        "name": "Public Data Extraction & Pipeline Bureau",
        "head_title": "Lead Data Automation Engineer",
        "description": "Builds high-resilience async scrapers, tabular parsers, and data cleaning pipelines.",
        "icon": "fa-solid fa-database",
        "base_price_usd": 45.0
    },
    {
        "domain": "micro_saas",
        "name": "Micro-SaaS & Fullstack Boilerplate Studio",
        "head_title": "Product Engineering Lead",
        "description": "Creates turn-key micro-SaaS boilerplates with auth, database, and UPI/Stripe checkout.",
        "icon": "fa-solid fa-layer-group",
        "base_price_usd": 79.0
    },
    {
        "domain": "security_hardening",
        "name": "API Security & Compliance Desk",
        "head_title": "Cybersecurity & Audit Lead",
        "description": "Provides JWT RBAC architectures, OWASP audit checklists, and rate-limiting modules.",
        "icon": "fa-solid fa-shield-halved",
        "base_price_usd": 59.0
    }
]

class EnterpriseGrowthEngine:
    def __init__(self):
        self._ensure_growth_state()

    def _ensure_growth_state(self):
        """Initializes or loads persistent self-growth state."""
        if not GROWTH_STATE_FILE.exists():
            initial = {
                "corporate_tier": 1,
                "tier_name": "Seed Startup",
                "total_evolutions": 0,
                "founded_departments_count": 0,
                "last_evolution_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                "reinvestment_pool_usd": 0.0,
                "dynamic_pricing_multiplier": 1.0
            }
            with open(GROWTH_STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(initial, f, indent=2)

    def get_growth_state(self) -> Dict[str, Any]:
        """Reads current growth and evolution metrics."""
        self._ensure_growth_state()
        try:
            with open(GROWTH_STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {"corporate_tier": 1, "tier_name": "Seed Startup", "total_evolutions": 0}

        finances = treasury.get_financial_summary()
        current_rev = finances.get("estimated_gross_revenue", 0.0)

        # Compute dynamic tier
        computed_tier = 1
        for tier_num in sorted(TIER_CONFIG.keys(), reverse=True):
            if current_rev >= TIER_CONFIG[tier_num]["min_revenue_usd"]:
                computed_tier = tier_num
                break

        cfg = TIER_CONFIG[computed_tier]
        data["corporate_tier"] = computed_tier
        data["tier_name"] = cfg["name"]
        data["tier_badge"] = cfg["badge"]
        data["base_price_usd"] = cfg["base_product_price_usd"]
        data["base_price_inr"] = round(cfg["base_product_price_usd"] * USD_TO_INR_RATE)
        data["current_gross_usd"] = current_rev
        data["total_departments"] = len(get_all_departments())
        return data

    def evaluate_and_grow(self) -> Dict[str, Any]:
        """
        Evaluates company progress and autonomously triggers self-expansion:
        1. Checks if company qualifies for a tier promotion.
        2. Detects if an emerging high-demand department should be founded.
        3. Updates pricing and logs corporate reinvestment.
        """
        state = self.get_growth_state()
        existing_depts = {d["dept_id"] for d in get_all_departments()}
        evolutions_made = []

        # 1. Check for autonomous department founding
        for domain_spec in EMERGING_DOMAINS_CATALOG:
            dept_id = f"dept_{domain_spec['domain']}"
            if dept_id not in existing_depts:
                # Found new department
                logger.info(f"🌱 Self-Growth: Founding new specialized department '{domain_spec['name']}'...")
                create_department(
                    dept_id=dept_id,
                    name=domain_spec["name"],
                    head_title=domain_spec["head_title"],
                    description=domain_spec["description"],
                    icon=domain_spec["icon"],
                    is_dynamic=True
                )
                evolutions_made.append(f"Founded Department: {domain_spec['name']}")
                
                # Log corporate reinvestment in Treasury
                treasury.log_transaction(
                    category="r_and_d",
                    description=f"Autonomous Department Launch: {domain_spec['name']}",
                    amount=0.0,
                    is_revenue=False
                )
                break  # Found one department per cycle

        # 2. Update state file
        if evolutions_made:
            state["total_evolutions"] = state.get("total_evolutions", 0) + len(evolutions_made)
            state["last_evolution_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
            state["founded_departments_count"] = state.get("founded_departments_count", 0) + len(evolutions_made)
            with open(GROWTH_STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)

        return {
            "tier": state["corporate_tier"],
            "tier_badge": state.get("tier_badge", "🌱 Tier 1"),
            "evolutions_triggered": evolutions_made,
            "status": "EXPANDED" if evolutions_made else "OPTIMIZED"
        }

    def compute_dynamic_product_price(self, category: str = "digital_product", complexity_score: float = 1.0) -> Tuple[float, int]:
        """Computes escalated product pricing based on corporate tier and asset depth."""
        state = self.get_growth_state()
        base_usd = state.get("base_price_usd", 19.0)
        
        # Multiply by complexity score (1.0 to 2.5)
        price_usd = round(base_usd * max(1.0, complexity_score), 2)
        price_inr = round(price_usd * USD_TO_INR_RATE)
        return price_usd, price_inr

# Global singleton
growth_engine = EnterpriseGrowthEngine()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Growth State:", growth_engine.get_growth_state())
    print("Growth Evaluation:", growth_engine.evaluate_and_grow())
