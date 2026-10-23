"""
MicroCorp AI - Digital Products Department
Produces commercial developer cheatsheets, prompt collections, and starter kits.
"""

from typing import Dict, Any
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from departments.base_department import BaseDepartment
from tools.gemini_client import llm_client
from tools.packager import packager
from core.agency_agents_manager import agency_agents_manager

SYSTEM_PROMPT = """You are the Senior Product Architect at MicroCorp AI.
Your mission is to produce ultra-high-quality, commercially viable digital products
(such as developer cheat sheets, system prompt engineering kits, API reference guides, and code boilerplates).
Every product must be clean, structured, comprehensive, and ready for immediate sale or distribution on Gumroad, itch.io, or GitHub Sponsors.
Format output strictly in GitHub Flavored Markdown with tables, code blocks, and clear sections.
"""

class DigitalProductsDepartment(BaseDepartment):
    def __init__(self):
        super().__init__(
            dept_id="dept_digital_products",
            name="Digital Asset & Product Lab",
            head_title="Chief Product Architect",
            description="Designs and packages commercial developer cheat sheets, prompt kits, and boilerplate starter packs.",
            icon="fa-box-open text-primary"
        )

    def process(self, task: Dict[str, Any], subagent_id: str) -> Dict[str, Any]:
        payload = task.get("payload", {})
        topic = payload.get("topic") or task.get("title", "Modern Python Async Architecture")
        product_type = payload.get("product_type", "Developer Cheatsheet & Pattern Kit")

        # Match specialized Agency persona from the 268+ fleet across 18 divisions
        agent_persona = agency_agents_manager.match_agent_for_task(
            title=topic,
            domain="engineering",
            requirements=product_type
        )
        effective_system_prompt = agency_agents_manager.build_persona_system_prompt(
            agent_persona,
            SYSTEM_PROMPT
        )

        prompt = f"""Create a commercial digital product on the topic: '{topic}'.
Product Type: {product_type}

Structure the document with:
1. # Product Title & Value Proposition
2. ## Quick Start & Core Concepts (with clean syntax table)
3. ## Production Code Patterns & Architecture Examples (detailed, copy-paste ready code)
4. ## Common Anti-Patterns & Gotchas to Avoid
5. ## Performance & Optimization Tips
6. ## Commercial License & Attribution Summary

Make it thorough, elegant, and directly useful for engineers.
"""
        generated_md, prompt_tokens, candidate_tokens = llm_client.generate(
            prompt=prompt,
            system_instruction=effective_system_prompt
        )

        title = f"{topic} - {product_type}"
        pkg = packager.save_deliverable(
            category="digital_product",
            title=title,
            markdown_content=generated_md,
            create_zip=True,
            agency_persona=agent_persona
        )

        persona_title = agent_persona.get('name') if agent_persona else 'Chief Product Architect'
        return {
            "title": title,
            "category": "digital_product",
            "deliverable_path": pkg["primary_path"],
            "summary": f"Manufactured and packaged {product_type} on '{topic}' by {persona_title}. Size: {pkg['size_bytes']} bytes.",
            "prompt_tokens": prompt_tokens,
            "completion_tokens": candidate_tokens,
            "agency_persona": agent_persona.get("name") if agent_persona else None,
            "agency_division": agent_persona.get("division") if agent_persona else None
        }

