"""
MicroCorp AI - Dynamic Product & Work Pricing Engine
Calculates tailored, differentiated pricing based on product type, code complexity,
and client contract scope.

Tiers:
1. Cheatsheets & Prompt Packs: ₹399 INR (~$4.99 USD)
2. Research Digests & Newsletters: ₹799 INR (~$9.99 USD)
3. Production Code Toolkits & Microservices: ₹1,799 INR (~$21.99 USD)
4. Enterprise Full-Stack & Autonomous Agent Systems: ₹3,999 INR (~$49.00 USD)
5. Turnkey Client Freelance Contracts: Dynamic based on client budget / agreed fee (e.g. ₹12,000 - ₹30,000 INR)
"""

import re
from typing import Dict, Any, Optional
from config import USD_TO_INR_RATE

PRICING_TIERS = {
    "cheatsheet": {
        "tier_id": "cheatsheet",
        "tier_name": "Developer Cheatsheet & Prompt Pack",
        "badge": "CHEATSHEET",
        "badge_style": "background: rgba(59, 130, 246, 0.2); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.4);",
        "price_usd": 4.99,
        "price_inr": 399,
        "description": "Quick-reference syntax cheat sheet, curated prompt templates, and actionable code patterns.",
        "keywords": ["cheatsheet", "cheat_sheet", "cheat", "prompt", "reference", "syntax", "quick", "chea", "sheet"]
    },
    "newsletter": {
        "tier_id": "newsletter",
        "tier_name": "Technical Research Digest",
        "badge": "RESEARCH DIGEST",
        "badge_style": "background: rgba(245, 158, 11, 0.2); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.4);",
        "price_usd": 9.99,
        "price_inr": 799,
        "description": "In-depth engineering analysis, architectural benchmarks, and emerging technology intelligence.",
        "keywords": ["newsletter", "digest", "intelligence", "report", "briefing", "analysis", "market"]
    },
    "developer_toolkit": {
        "tier_id": "developer_toolkit",
        "tier_name": "Production Code Toolkit & Microservice",
        "badge": "PRODUCTION TOOLKIT",
        "badge_style": "background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.4);",
        "price_usd": 21.99,
        "price_inr": 1799,
        "description": "Battle-tested microservice boilerplate, Docker scaffolding, unit test suites, and commercial license.",
        "keywords": ["toolkit", "developer_toolkit", "microservice", "boilerplate", "fastapi", "backend", "docker", "starter", "webhook"]
    },
    "full_stack": {
        "tier_id": "full_stack",
        "tier_name": "Enterprise Full-Stack & Agent Suite",
        "badge": "ENTERPRISE SYSTEM",
        "badge_style": "background: rgba(168, 85, 247, 0.2); color: #c084fc; border: 1px solid rgba(168, 85, 247, 0.4);",
        "price_usd": 49.00,
        "price_inr": 3999,
        "description": "End-to-end full-stack platform with JWT authentication, database migrations, autonomous agent orchestration, and production deployment scripts.",
        "keywords": ["full_stack", "full-stack", "fullstack", "saas", "autonomous_agent", "agent_lab", "security_hardening", "jwt_auth", "enterprise"]
    },
    "freelance_turnkey": {
        "tier_id": "freelance_turnkey",
        "tier_name": "Turnkey Client Freelance Contract",
        "badge": "CLIENT CONTRACT",
        "badge_style": "background: rgba(236, 72, 153, 0.2); color: #f472b6; border: 1px solid rgba(236, 72, 153, 0.4);",
        "price_usd": 250.00,
        "price_inr": 21500,
        "description": "Custom-built, 100% turnkey client software delivery with comprehensive setup walkthrough, quality guarantee, and full commercial transfer.",
        "keywords": ["freelance", "fiverr", "upwork", "contract", "client_order", "turnkey", "proposal"]
    }
}

class ProductPricingEngine:
    def __init__(self):
        self.tiers = PRICING_TIERS
        self.usd_to_inr = USD_TO_INR_RATE

    def classify_asset(self, title: str = "", category: Optional[str] = None) -> str:
        """
        Classifies an asset into one of the 5 defined pricing tiers based on
        its title and category.
        """
        text = f"{title} {category or ''}".lower()

        # 1. Check for client contract / freelance delivery
        if any(k in text for k in self.tiers["freelance_turnkey"]["keywords"]):
            return "freelance_turnkey"

        # 2. Check for enterprise full-stack / multi-agent / security
        if any(k in text for k in self.tiers["full_stack"]["keywords"]):
            return "full_stack"

        # 3. Check for cheatsheet / prompt pack
        if any(k in text for k in self.tiers["cheatsheet"]["keywords"]):
            return "cheatsheet"

        # 4. Check for newsletter / research digest
        if any(k in text for k in self.tiers["newsletter"]["keywords"]):
            return "newsletter"

        # 5. Default to production developer toolkit / microservice
        return "developer_toolkit"

    def get_pricing_for_asset(
        self,
        title: str = "",
        category: Optional[str] = None,
        custom_price_usd: Optional[float] = None,
        custom_price_inr: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Returns full pricing metadata for a specific product or work order.
        Respects custom price overrides if explicitly provided.
        """
        tier_id = self.classify_asset(title=title, category=category)
        tier_def = self.tiers.get(tier_id, self.tiers["developer_toolkit"])

        if custom_price_inr is not None and custom_price_inr > 0:
            price_inr = round(custom_price_inr)
            price_usd = custom_price_usd if custom_price_usd else round(price_inr / self.usd_to_inr, 2)
            is_custom = True
        elif custom_price_usd is not None and custom_price_usd > 0:
            price_usd = round(custom_price_usd, 2)
            price_inr = round(price_usd * self.usd_to_inr)
            is_custom = True
        else:
            price_usd = tier_def["price_usd"]
            price_inr = tier_def["price_inr"]
            is_custom = False

        return {
            "tier_id": tier_id,
            "tier_name": tier_def["tier_name"],
            "badge": tier_def["badge"],
            "badge_style": tier_def["badge_style"],
            "price_usd": price_usd,
            "price_inr": price_inr,
            "description": tier_def["description"],
            "is_custom_quote": is_custom
        }

    def get_catalog(self) -> Dict[str, Any]:
        """Returns the public catalog of pricing tiers."""
        return {
            "usd_to_inr_rate": self.usd_to_inr,
            "tiers": self.tiers
        }

# Global singleton
pricing_engine = ProductPricingEngine()
