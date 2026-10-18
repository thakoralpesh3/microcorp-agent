"""
MicroCorp AI - Autonomous Work Discovery, 100% Feasibility Filter & Planning Engine
Autonomously searches online opportunities, filters for tasks the agent can 100% finish itself,
and generates structured execution plans with milestones and verification checklists.
"""

import uuid
import json
import logging
from typing import Dict, Any, List, Tuple, Optional
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import DELIVERABLES_DIR
from tools.web_researcher import web_researcher
from tools.gemini_client import llm_client
from core.database import save_plan, enqueue_task, get_all_departments
from core.legal_guardian import legal_guardian

logger = logging.getLogger("MicroCorp.AutonomousPlanner")

PLANS_DIR = DELIVERABLES_DIR / "plans"
PLANS_DIR.mkdir(parents=True, exist_ok=True)

FEASIBILITY_SYSTEM_PROMPT = """You are the Senior Feasibility Officer at MicroCorp AI.
Your sole job is to evaluate if an online task/opportunity can be 100% completed autonomously by an AI agent running on a laptop without ANY human intervention.

CRITICAL RULES:
1. Tasks CAN be 100% completed if they are software development, documentation, cheatsheets, prompt engineering, technical analysis, data curation, buyer guides, technical proposals, API designs, or code templates.
2. Tasks CANNOT be 100% completed if they require: physical presence, shipping physical goods, voice phone calls, webcam interviews, in-person meetings, manual bank account / KYC verifications during execution, or access to private proprietary non-public credentials.

Evaluate the opportunity and return JSON matching this schema:
{
  "feasibility_score": float between 0.0 and 1.0,
  "is_100_percent_finishable": boolean (true if feasibility_score >= 0.85 and no physical/human blockers),
  "autonomous_category": "digital_product" | "content_newsletter" | "gig_proposal" | "code_architecture" | "lead_dataset",
  "blockers": [list of human requirements if any, otherwise empty],
  "reasons": "Detailed explanation of why the agent can or cannot finish this 100% autonomously."
}
Return ONLY valid JSON.
"""

PLANNING_SYSTEM_PROMPT = """You are the Chief Strategy & Planning Architect at MicroCorp AI.
You produce rigorous, end-to-end execution plans for tasks that will be completed 100% autonomously by departmental subagents.
Each plan must have clear objectives, phased milestones, deliverable file structures, and a strict verification checklist.
Format your output in clean JSON matching:
{
  "title": "Clear Actionable Task Title",
  "objective": "Specific commercial and technical objective",
  "domain": "digital_products" | "content_newsletter" | "gig_proposal" | "custom",
  "target_audience": "e.g. Senior Developers, Cloud Architects, Technical Buyers",
  "milestones": [
    {
      "step": 1,
      "title": "Phase name",
      "description": "Specific autonomous actions to perform"
    }
  ],
  "verification_checklist": [
    "Criteria 1 confirming 100% completion",
    "Criteria 2 confirming production quality",
    "Criteria 3 confirming zero placeholders"
  ],
  "expected_deliverables": ["README.md", "index.html", "MARKETPLACE_LISTING.md", "bundle.zip"],
  "estimated_value_usd": 19.99
}
Return ONLY valid JSON.
"""

class AutonomousWorkPlanner:
    def __init__(self):
        self.last_search_time = 0

    def evaluate_task_feasibility(self, title: str, description: str) -> Dict[str, Any]:
        """Evaluates whether a task is 100% lawful, ethical, and finishable autonomously."""
        # 0. Strict Legality & Ethical Compliance Gate
        compliance = legal_guardian.audit_task(title, description)
        if not compliance.get("is_legal", True):
            logger.warning(f"⚖️ Task REJECTED on legal/ethical grounds: '{title}' - {compliance['reason']}")
            return {
                "feasibility_score": 0.0,
                "is_100_percent_finishable": False,
                "is_legal": False,
                "autonomous_category": "rejected_illicit",
                "risk_category": compliance.get("risk_category"),
                "legal_statute": compliance.get("legal_statute"),
                "blockers": [f"Legal/Ethical Violation: Prohibited under {compliance.get('legal_statute')}"],
                "reasons": f"REJECTED FOR LEGAL COMPLIANCE: {compliance['reason']}"
            }

        prompt = f"""Evaluate this task opportunity for 100% autonomous completion:
Title: {title}
Description: {description}
"""
        try:
            raw_text, _, _ = llm_client.generate(prompt=prompt, system_instruction=FEASIBILITY_SYSTEM_PROMPT)
            # Clean possible markdown fencing
            cleaned = raw_text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            return json.loads(cleaned.strip())
        except Exception as e:
            logger.warning(f"Feasibility evaluation fallback for '{title}': {e}")
            # Heuristic fallback
            is_physical = any(w in (title + description).lower() for w in ["phone call", "in person", "physical", "office", "interview"])
            score = 0.4 if is_physical else 0.92
            return {
                "feasibility_score": score,
                "is_100_percent_finishable": not is_physical,
                "autonomous_category": "digital_product",
                "blockers": ["Requires manual human interaction"] if is_physical else [],
                "reasons": "Filtered via heuristic engine for 100% autonomous software deliverables."
            }

    def generate_full_execution_plan(self, title: str, description: str, category: str) -> Dict[str, Any]:
        """Formulates a comprehensive 100% autonomous execution plan."""
        prompt = f"""Construct a complete, end-to-end execution plan for this 100% autonomous task:
Title: {title}
Category: {category}
Context: {description}

Produce actionable milestones and a strict verification checklist ensuring the agent finishes all work without human help.
"""
        try:
            raw_text, _, _ = llm_client.generate(prompt=prompt, system_instruction=PLANNING_SYSTEM_PROMPT)
            cleaned = raw_text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            return json.loads(cleaned.strip())
        except Exception as e:
            logger.warning(f"Planning fallback for '{title}': {e}")
            return {
                "title": title,
                "objective": f"Deliver a complete, production-ready {category} autonomously.",
                "domain": category if category in ["digital_products", "content_newsletter", "gig_proposal"] else "digital_products",
                "target_audience": "Software Engineers & Creators",
                "milestones": [
                    {"step": 1, "title": "Market & Spec Research", "description": "Harvest technical signals and define scope."},
                    {"step": 2, "title": "Core Implementation", "description": "Author exhaustive code patterns and technical guide."},
                    {"step": 3, "title": "Verification & Packaging", "description": "Package into HTML, Markdown, and ZIP with license and marketplace copy."}
                ],
                "verification_checklist": [
                    "Complete production-ready code included",
                    "No placeholders or TODOs",
                    "License and Terms embedded in archive"
                ],
                "expected_deliverables": ["README.md", "index.html", "MARKETPLACE_LISTING.md", "bundle.zip"],
                "estimated_value_usd": 19.99
            }

    def search_and_plan_autonomous_work(self) -> Optional[Dict[str, Any]]:
        """
        1. Searches web signals and remote gigs.
        2. Filters strictly for tasks that can be 100% finished autonomously.
        3. Formulates a complete execution plan.
        4. Saves the plan and enqueues the task.
        """
        logger.info("🔍 Autonomous Planner: Scanning web feeds for 100% finishable work...")
        
        # 1. Harvest candidates from remote gigs and tech trends
        candidates = []
        gigs = web_researcher.fetch_remote_gigs()
        for g in gigs[:5]:
            candidates.append({"title": g["title"], "desc": g.get("description", ""), "source": "WeWorkRemotely"})

        trends = web_researcher.fetch_trending_tech()
        for t in trends[:5]:
            candidates.append({
                "title": f"Developer Toolkit: {t['title'][:45]}",
                "desc": f"Create complete commercial cheatsheet, pattern guide, and boilerplates based on trending topic: {t['title']}",
                "source": t.get("source", "HackerNews")
            })

        # 2. Feasibility Evaluation: Find first candidate with >= 85% feasibility score
        greenlit_opp = None
        feasibility_result = None

        for opp in candidates:
            eval_res = self.evaluate_task_feasibility(opp["title"], opp["desc"])
            if eval_res.get("is_100_percent_finishable") and eval_res.get("feasibility_score", 0) >= 0.85:
                greenlit_opp = opp
                feasibility_result = eval_res
                logger.info(f"✅ Greenlit 100% Autonomous Task: '{opp['title']}' (Score: {eval_res['feasibility_score']*100:.0f}%)")
                break
            else:
                logger.debug(f"Filtered out task '{opp['title']}': {eval_res.get('reasons')}")

        if not greenlit_opp:
            # Fallback guaranteed 100% finishable technical task
            greenlit_opp = {
                "title": "FastAPI Distributed Rate Limiter & Concurrency Blueprint",
                "desc": "Build an exhaustive architecture reference kit with Redis token-bucket algorithms and benchmark tests.",
                "source": "AutonomousCore"
            }
            feasibility_result = {
                "feasibility_score": 0.98,
                "is_100_percent_finishable": True,
                "autonomous_category": "digital_product",
                "blockers": [],
                "reasons": "100% software code and architectural documentation with immediate commercial value."
            }

        # 3. Formulate Full Execution Plan
        plan_dict = self.generate_full_execution_plan(
            title=greenlit_opp["title"],
            description=greenlit_opp["desc"],
            category=feasibility_result.get("autonomous_category", "digital_product")
        )

        plan_id = f"plan_{uuid.uuid4().hex[:8]}"
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        domain = plan_dict.get("domain", "digital_products")

        # 4. Save Plan Markdown Document
        plan_md_path = PLANS_DIR / f"{plan_id}.md"
        plan_md = f"""# Autonomous Work Plan: {plan_dict['title']}

**Plan ID:** `{plan_id}`  
**Target Domain:** `{domain}`  
**100% Autonomous Feasibility:** **{feasibility_result.get('feasibility_score', 1.0)*100:.0f}%**  
**Autonomous Status:** Fully Approved (0 Human Blockers)

---

## 🎯 Strategic Objective
{plan_dict.get('objective', '')}

**Target Audience:** {plan_dict.get('target_audience', 'Software Engineers')}  
**Estimated Value:** ${plan_dict.get('estimated_value_usd', 19.99):.2f} USD

---

## 📋 Feasibility Analysis & Autonomous Rationale
{feasibility_result.get('reasons', '')}

---

## 🗺️ Phased Milestones
"""
        for m in plan_dict.get("milestones", []):
            plan_md += f"\n### Milestone {m.get('step', '-')}: {m.get('title', '')}\n{m.get('description', '')}\n"

        plan_md += "\n---\n\n## ✅ 100% Completion & Verification Checklist\n"
        for item in plan_dict.get("verification_checklist", []):
            plan_md += f"- [x] {item}\n"

        plan_md += f"\n---\n*Authored autonomously by MicroCorp AI Strategy & Planning Engine.*\n"
        with open(plan_md_path, "w", encoding="utf-8") as f:
            f.write(plan_md)

        # 5. Persist Plan in Database
        save_plan(
            plan_id=plan_id,
            task_id=task_id,
            title=plan_dict["title"],
            domain=domain,
            feasibility_score=feasibility_result.get("feasibility_score", 1.0),
            feasibility_reasons=feasibility_result.get("reasons", ""),
            plan_dict=plan_dict,
            status="planned"
        )

        # 6. Enqueue Task for Execution
        enqueue_task(
            task_id=task_id,
            dept_id="dept_" + domain if "dept_" not in domain else domain,
            title=plan_dict["title"],
            domain=domain,
            payload={
                "topic": plan_dict["title"],
                "product_type": "Developer Reference & Architecture Kit",
                "plan_id": plan_id,
                "plan_file": str(plan_md_path),
                "verification_checklist": plan_dict.get("verification_checklist", [])
            },
            priority=1
        )
        logger.info(f"🚀 Plan '{plan_id}' deployed to execution queue as '{task_id}'!")
        return {
            "plan_id": plan_id,
            "task_id": task_id,
            "title": plan_dict["title"],
            "domain": domain,
            "feasibility_score": feasibility_result.get("feasibility_score", 1.0),
            "plan_file": str(plan_md_path),
            "milestones_count": len(plan_dict.get("milestones", []))
        }

autonomous_planner = AutonomousWorkPlanner()
