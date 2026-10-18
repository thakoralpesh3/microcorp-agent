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
            system_instruction=SYSTEM_PROMPT
        )

        title = f"{topic} - {product_type}"
        pkg = packager.save_deliverable(
            category="digital_product",
            title=title,
            markdown_content=generated_md,
            create_zip=True
        )

        return {
            "title": title,
            "category": "digital_product",
            "deliverable_path": pkg["primary_path"],
            "summary": f"Manufactured and packaged {product_type} on '{topic}'. Size: {pkg['size_bytes']} bytes.",
            "prompt_tokens": prompt_tokens,
            "completion_tokens": candidate_tokens
        }
