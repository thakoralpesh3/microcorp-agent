"""
MicroCorp AI - Market Intelligence & Discovery Department
Harvests market signals, discovers revenue opportunities, and feeds high-yield tasks to departments.
"""

from typing import Dict, Any, List
from pathlib import Path
import sys
import uuid

sys.path.insert(0, str(Path(__file__).parent.parent))
from departments.base_department import BaseDepartment
from tools.web_researcher import web_researcher
from tools.gemini_client import llm_client
from tools.packager import packager
from core.database import enqueue_task

SYSTEM_PROMPT = """You are the Chief Intelligence Analyst at MicroCorp AI.
Your responsibility is to analyze raw market signals, web feeds, and developer trends,
and turn them into high-value structured intelligence, niche datasets, and revenue-generating task backlogs.
"""

class IntelligenceDepartment(BaseDepartment):
    def __init__(self):
        super().__init__(
            dept_id="dept_intelligence",
            name="Market Intelligence & Opportunity Radar",
            head_title="Chief Intelligence Analyst",
            description="Scans the web for viral trends, commercial digital product niches, and feeds task pipelines.",
            icon="fa-radar text-warning"
        )

    def process(self, task: Dict[str, Any], subagent_id: str) -> Dict[str, Any]:
        payload = task.get("payload", {})
        action = payload.get("action", "generate_sprint_tasks")
        
        # 1. Harvest live web signals
        trends = web_researcher.fetch_trending_tech()
        gigs = web_researcher.fetch_remote_gigs()

        trend_text = "\n".join([f"- {t['title']} ({t['source']})" for t in trends[:6]])
        gig_text = "\n".join([f"- {g['title']}" for g in gigs[:4]])

        prompt = f"""Analyze the following live market signals and generate a Market Intelligence Report + 3 actionable sprint tasks:
Current Tech Signals:
{trend_text}

Active Remote Gig Demands:
{gig_text}

Output format:
1. # Market Intelligence Brief & Commercial Signal Report
2. ## Top Emerging Opportunities (Why these matter right now)
3. ## High-Yield Deliverables to Create Immediately
4. ## Curated B2B Resource & Dataset (Structured markdown list of 5 valuable tools/resources)
"""
        generated_md, prompt_tokens, candidate_tokens = llm_client.generate(
            prompt=prompt,
            system_instruction=SYSTEM_PROMPT
        )

        title = "Market Opportunity Intelligence & Trend Radar"
        pkg = packager.save_deliverable(
            category="lead_dataset",
            title=title,
            markdown_content=generated_md,
            create_zip=False
        )

        # Autonomously seed next sprint tasks into other departments
        # 1. Seed a digital product task
        if trends:
            enqueue_task(
                task_id=f"task_dp_{uuid.uuid4().hex[:6]}",
                dept_id="dept_digital_products",
                title=f"Developer Guide: {trends[0]['title'][:50]}",
                domain="digital_products",
                payload={"topic": trends[0]["title"], "product_type": "Developer Cheatsheet & Pattern Kit"},
                priority=3
            )
        # 2. Seed a newsletter task
        enqueue_task(
            task_id=f"task_nl_{uuid.uuid4().hex[:6]}",
            dept_id="dept_content_newsletter",
            title="Weekly Developer Tech & AI Signals Digest",
            domain="content_newsletter",
            payload={"topic": "Autonomous Agents & Modern Local Development", "content_type": "newsletter"},
            priority=4
        )

        return {
            "title": title,
            "category": "lead_dataset",
            "deliverable_path": pkg["primary_path"],
            "summary": "Synthesized market radar and populated sprint pipeline with new passive income tasks.",
            "prompt_tokens": prompt_tokens,
            "completion_tokens": candidate_tokens
        }
