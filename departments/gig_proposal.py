"""
MicroCorp AI - Gig & Proposal Department
Monitors remote job opportunities and drafts high-conversion client bids.
"""

from typing import Dict, Any
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from departments.base_department import BaseDepartment
from tools.gemini_client import llm_client
from tools.packager import packager
from tools.web_researcher import web_researcher

SYSTEM_PROMPT = """You are the Lead Business Development Partner at MicroCorp AI.
Your job is to draft winning, highly tailored proposals and quotes for software contracts and gigs.
Avoid generic fluff. Provide clear technical insight, realistic timelines, structured milestones,
and confident communication that shows deep engineering competence.
"""

class GigProposalDepartment(BaseDepartment):
    def __init__(self):
        super().__init__(
            dept_id="dept_gig_proposal",
            name="Client Acquisition & Proposal Desk",
            head_title="Lead BD Partner",
            description="Monitors remote project opportunities and crafts tailored, high-converting client proposals.",
            icon="fa-file-signature text-success"
        )

    def process(self, task: Dict[str, Any], subagent_id: str) -> Dict[str, Any]:
        payload = task.get("payload", {})
        job_title = payload.get("job_title") or task.get("title", "Python Web Automation Specialist")
        job_description = payload.get("job_description", "")
        client_link = payload.get("link", "")

        if not job_description:
            # If no description provided, pull from live remote feeds
            live_gigs = web_researcher.fetch_remote_gigs()
            if live_gigs:
                job_title = live_gigs[0]["title"]
                job_description = live_gigs[0]["description"]
                client_link = live_gigs[0]["link"]

        # Strict Legal Audit of Customer / Client Request
        from core.legal_guardian import legal_guardian
        order_audit = legal_guardian.audit_customer_order(
            project_title=job_title,
            requirements=job_description,
            client_name=payload.get("client_name")
        )

        if not order_audit.get("is_legal", True):
            # Prohibited customer work: strictly reject and issue official Refusal Notice
            rejection_md = order_audit["rejection_notice_md"]
            title = f"Refusal Notice - {job_title}"
            pkg = packager.save_deliverable(
                category="freelance_proposal",
                title=title,
                markdown_content=rejection_md,
                create_zip=False
            )
            return {
                "title": title,
                "category": "freelance_proposal",
                "deliverable_path": pkg["primary_path"],
                "summary": f"CUSTOMER WORK REJECTED: Prohibited work request ({order_audit['risk_category']}). Formal refusal notice issued.",
                "is_rejected": True,
                "rejection_advisory": order_audit["advisory_summary"],
                "prompt_tokens": 0,
                "completion_tokens": 0
            }

        prompt = f"""Draft a professional, high-converting proposal for the following client project:
Job Title: {job_title}
Client Job Description:
{job_description}
Reference Link: {client_link}

Structure the Proposal:
1. # Proposal: {job_title}
2. ## Executive Summary & Understanding of Your Problem (Directly addressing client's core bottleneck)
3. ## Proposed Technical Architecture & Deliverables (Step-by-step implementation plan)
4. ## Phased Milestones & Timeline (Milestone 1, 2, 3 with estimated completion days)
5. ## Commercial Quote & Pricing Breakdown (Estimated project fee and deliverables guarantee)
6. ## Relevant Experience & Why We Are The Best Fit
7. ## Next Steps & Call to Action
"""
        generated_md, prompt_tokens, candidate_tokens = llm_client.generate(
            prompt=prompt,
            system_instruction=SYSTEM_PROMPT
        )

        title = f"Proposal - {job_title}"
        pkg = packager.save_deliverable(
            category="freelance_proposal",
            title=title,
            markdown_content=generated_md,
            create_zip=False
        )

        return {
            "title": title,
            "category": "freelance_proposal",
            "deliverable_path": pkg["primary_path"],
            "summary": f"Drafted tailored proposal for '{job_title}'. Saved to deliverables vault.",
            "prompt_tokens": prompt_tokens,
            "completion_tokens": candidate_tokens
        }
