"""
MicroCorp AI - Content & Newsletter Department
Synthesizes weekly tech/AI trend digests and affiliate product buyer guides.
"""

from typing import Dict, Any
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from departments.base_department import BaseDepartment
from tools.gemini_client import llm_client
from tools.packager import packager
from tools.web_researcher import web_researcher

SYSTEM_PROMPT = """You are the Lead Editorial Director at MicroCorp AI.
You write engaging, deeply analytical, and monetizable tech digests and buyer comparison guides.
Your style is sharp, insightful, and publication-ready.
Always include executive summaries, comparative tables, pros/cons, and actionable takeaways.
"""

class ContentNewsletterDepartment(BaseDepartment):
    def __init__(self):
        super().__init__(
            dept_id="dept_content_newsletter",
            name="Editorial & Trend Digest Bureau",
            head_title="Editorial Director",
            description="Synthesizes weekly AI trend digests, sponsor-ready newsletters, and affiliate buyer guides.",
            icon="fa-newspaper text-info"
        )

    def process(self, task: Dict[str, Any], subagent_id: str) -> Dict[str, Any]:
        payload = task.get("payload", {})
        content_type = payload.get("content_type", "newsletter") # 'newsletter' or 'affiliate_guide'
        topic = payload.get("topic") or task.get("title", "Weekly AI & Autonomous Agent Breakthroughs")

        # Gather real-time market data
        real_trends = web_researcher.fetch_trending_tech()
        trend_context = "\n".join([f"- {t['title']} ({t['source']}): {t.get('description', '')[:100]}" for t in real_trends[:5]])

        if content_type == "affiliate_guide":
            prompt = f"""Write an in-depth, affiliate-monetized Buyer's Guide and Product Comparison on: '{topic}'.
Include:
1. # The Definitive Buyer's Guide: {topic}
2. ## Quick Comparison Matrix (Markdown Table: Features, Performance, Value, Verdict)
3. ## Top 3 Recommended Solutions / Products (Detailed Review, Key Benefits, Trade-offs)
4. ## Who Should Buy What (Persona & Budget Recommendations)
5. ## Buying Checklist & FAQ
6. ## [Affiliate Disclaimer & Recommended Purchase Links]

Context from current market discussions:
{trend_context}
"""
            cat = "affiliate_guide"
        else:
            prompt = f"""Write a comprehensive weekly edition of the Tech & AI Trend Digest on: '{topic}'.
Context from live developer signals:
{trend_context}

Structure:
1. # Tech Signals: {topic}
2. ## 🚀 The Big Breakthrough (Deep dive into the most important story)
3. ## ⚡ Quick Bites & Developer Pulse (4-5 key updates with technical context)
4. ## 🛠️ Tool of the Week (Practical utility, installation, and usage command)
5. ## 💡 Founder / Builder Insight (Actionable perspective on shipping software)
6. ## [Sponsor & Community Shoutout Section]
"""
            cat = "newsletter_edition"

        generated_md, prompt_tokens, candidate_tokens = llm_client.generate(
            prompt=prompt,
            system_instruction=SYSTEM_PROMPT
        )

        title = f"{topic} ({cat.replace('_', ' ').title()})"
        pkg = packager.save_deliverable(
            category=cat,
            title=title,
            markdown_content=generated_md,
            create_zip=False
        )

        return {
            "title": title,
            "category": cat,
            "deliverable_path": pkg["primary_path"],
            "summary": f"Published {cat} on '{topic}'. Live HTML preview available.",
            "prompt_tokens": prompt_tokens,
            "completion_tokens": candidate_tokens
        }
