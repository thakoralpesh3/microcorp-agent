"""
MicroCorp AI - CEO Orchestrator & Executive Core
Directs company strategy, manages sprints, coordinates departments, and balances workload.
"""

import time
import asyncio
import threading
import logging
import uuid
from typing import Dict, Any, Optional
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import CEO_NAME, COMPANY_NAME, LOOP_INTERVAL_SECONDS, AUTO_SPRINT_INTERVAL_MINUTES
from core.database import (
    fetch_pending_task, enqueue_task, get_queue_stats, 
    get_all_departments, get_active_subagents
)
from core.resource_guardian import guardian
from core.department_scaler import scaler
from core.treasury import treasury
from core.legal_guardian import legal_guardian
from core.git_sync import git_sync
from config import ENABLE_PUBLIC_TUNNEL, ENABLE_GITHUB_RELEASES

# Import Core Departments
from departments.intelligence import IntelligenceDepartment
from departments.digital_products import DigitalProductsDepartment
from departments.content_newsletter import ContentNewsletterDepartment
from departments.gig_proposal import GigProposalDepartment

logger = logging.getLogger("MicroCorp.CEO")

class CEOOrchestrator:
    def __init__(self):
        self.name = CEO_NAME
        self.company = COMPANY_NAME
        self.is_running = False
        self.is_paused = False
        self._thread: Optional[threading.Thread] = None
        self._loop_count = 0
        self.last_auto_sprint_time = 0

        # Initialize and register core departments
        self.intelligence_dept = IntelligenceDepartment()
        self.digital_products_dept = DigitalProductsDepartment()
        self.content_newsletter_dept = ContentNewsletterDepartment()
        self.gig_proposal_dept = GigProposalDepartment()

        scaler.register_department(self.intelligence_dept)
        scaler.register_department(self.digital_products_dept)
        scaler.register_department(self.content_newsletter_dept)
        scaler.register_department(self.gig_proposal_dept)

    def start(self):
        """Starts the autonomous executive loop and public tunnel in background threads."""
        if self.is_running:
            return
        self.is_running = True
        self.is_paused = False
        
        # Start public Cloudflare tunnel if enabled
        if ENABLE_PUBLIC_TUNNEL:
            try:
                from core.tunnel_gateway import public_gateway
                public_gateway.start_tunnel()
            except Exception as e:
                logger.warning(f"Could not start public Cloudflare tunnel: {e}")

        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="CEO-Orchestrator")
        self._thread.start()
        logger.info(f"👑 CEO {self.name} has assumed command of {self.company}.")

    def stop(self):
        self.is_running = False
        try:
            from core.tunnel_gateway import public_gateway
            public_gateway.stop_tunnel()
        except Exception:
            pass
        logger.info(f"👑 CEO {self.name} paused enterprise operations.")

    def trigger_sprint(self, domain: Optional[str] = None, custom_title: Optional[str] = None, payload: Optional[Dict[str, Any]] = None) -> str:
        """Manually or programmatically triggers a sprint task, strictly enforcing legal compliance."""
        dom = domain or "intelligence"
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        title = custom_title or f"Autonomous Sprint Task ({dom.replace('_', ' ').title()})"
        
        # 0. Strict Legal Compliance Screening
        audit = legal_guardian.audit_task(title, payload or {}, domain=dom)
        if not audit["is_legal"]:
            logger.warning(f"⚖️ Sprint rejected by Legal Guardian: '{title}' [{audit['risk_category']}]")
            raise ValueError(audit["reason"])

        dept = scaler.get_department_for_domain(dom)
        dept_id = dept.dept_id if dept else "dept_intelligence"

        enqueue_task(
            task_id=task_id,
            dept_id=dept_id,
            title=title,
            domain=dom,
            payload=payload or {},
            priority=1
        )
        logger.info(f"Enqueued high-priority sprint task: {title} ({task_id})")
        return task_id

    def _run_loop(self):
        """Continuous executive background loop."""
        # Initial boot sprint if queue is completely empty
        stats = get_queue_stats()
        if stats["total_pending"] == 0 and stats["total_completed"] == 0:
            logger.info("Fresh enterprise boot: Seeding initial market radar task...")
            self.trigger_sprint(
                domain="intelligence",
                custom_title="Initial Market Radar & Opportunity Discovery",
                payload={"action": "bootstrap_pipeline"}
            )

        while self.is_running:
            try:
                self._loop_count += 1
                
                if self.is_paused:
                    time.sleep(2)
                    continue

                # 1. Hardware safety check
                is_safe, safety_msg = guardian.evaluate_safety()
                if not is_safe:
                    logger.warning(f"Executive Loop Throttled: {safety_msg}")
                    time.sleep(LOOP_INTERVAL_SECONDS)
                    continue

                # 2. Workload Analysis & Subagent/Department Auto-Scaling
                scale_res = scaler.check_and_scale_workload()

                # 3. Task Execution Cycle
                task = fetch_pending_task()
                if task:
                    domain = task["domain"]
                    dept = scaler.get_department_for_domain(domain)
                    if not dept:
                        # Dynamically generate on-demand department
                        dept = scaler.create_dynamic_department(domain)

                    logger.info(f"CEO delegating '{task['title']}' to {dept.name}...")
                    try:
                        dept.execute_task(task)
                    except Exception as e:
                        logger.error(f"Task execution failed: {e}")
                else:
                    # Queue is empty - Self-Execution Engine triggers next autonomous income sprint
                    now = time.time()
                    if (now - self.last_auto_sprint_time) >= (AUTO_SPRINT_INTERVAL_MINUTES * 60):
                        self.last_auto_sprint_time = now
                        logger.info("⚡ Autonomous Self-Execution Engine: Triggering scheduled income sprint...")
                        self.run_autonomous_income_cycle()

                # 4. Record Telemetry Snapshot
                active_subs = len(get_active_subagents())
                q_stats = get_queue_stats()
                guardian.log_telemetry_snapshot(active_subagents=active_subs, queue_depth=q_stats["total_pending"])

            except Exception as e:
                logger.error(f"Error in CEO executive loop: {e}", exc_info=True)

            time.sleep(LOOP_INTERVAL_SECONDS)

    def run_autonomous_income_cycle(self):
        """Autonomously searches online opportunities, filters for 100% finishable work, plans, executes, and publishes."""
        from core.growth_engine import growth_engine
        # 1. Trigger corporate self-growth and dynamic department evaluation
        try:
            growth_res = growth_engine.evaluate_and_grow()
            if growth_res.get("evolutions_triggered"):
                logger.info(f"🌱 Enterprise Growth Event: {growth_res['evolutions_triggered']}")
        except Exception as e:
            logger.debug(f"Growth evaluation error: {e}")

        # 2. Search, plan and enqueue 100% turnkey work
        plan_res = None
        try:
            from core.autonomous_planner import autonomous_planner
            plan_res = autonomous_planner.search_and_plan_autonomous_work()
            if plan_res:
                logger.info(f"✨ Autonomous Strategy: Greenlit plan '{plan_res['title']}' with {plan_res['feasibility_score']*100:.0f}% feasibility.")
        except Exception as e:
            logger.warning(f"Planner exception, using fallback opportunity rotation: {e}")
            from tools.web_researcher import web_researcher
            trends = web_researcher.fetch_trending_tech()
            topic = trends[0]["title"] if trends else "Python Cloud Microservices"
            self.trigger_sprint(
                domain="digital_products",
                custom_title=f"Autonomous Asset: {topic[:45]}",
                payload={"topic": topic, "product_type": "Developer Reference & Architecture Kit"}
            )

        # 2b. Autonomous Turnkey Freelance Execution (Fiverr / Upwork / Freelancer)
        try:
            freelance_res = self.run_freelance_sprint()
            if freelance_res and freelance_res.get("status") == "COMPLETED":
                logger.info(f"💼 Autonomous Turnkey Freelance Delivery Completed: '{freelance_res.get('title')}' on {freelance_res.get('platform')}. Net: ${freelance_res.get('net_passive_income')}")
        except Exception as e:
            logger.debug(f"Autonomous freelance sprint notice: {e}")

        # 3. Public GitHub Release Distribution for top completed package
        if ENABLE_GITHUB_RELEASES:
            try:
                from core.public_distribution import public_distribution
                from config import DELIVERABLES_DIR
                ready_dir = DELIVERABLES_DIR / "ready_to_monetize"
                if ready_dir.exists():
                    zip_files = sorted(ready_dir.glob("*.zip"), key=os.path.getmtime, reverse=True)
                    if zip_files:
                        latest_zip = zip_files[0]
                        title_clean = latest_zip.stem.replace("_", " ").title()
                        price_usd, price_inr = growth_engine.compute_dynamic_product_price(complexity_score=1.2)
                        public_distribution.publish_asset_to_github_release(
                            zip_path=str(latest_zip),
                            title=title_clean,
                            description=f"Autonomous production-grade toolkit on {title_clean}.",
                            price_usd=price_usd,
                            price_inr=price_inr
                        )
            except Exception as e:
                logger.debug(f"Public distribution error: {e}")

        # 4. Two-Way GitHub State Synchronization
        try:
            self.sync_with_github("auto: autonomous enterprise cycle sync to GitHub")
        except Exception as e:
            logger.debug(f"Autonomous git sync notice: {e}")

        return plan_res

    # Backward compatibility alias
    run_daily_income_cycle = run_autonomous_income_cycle

    def run_freelance_sprint(self, job_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Harvests freelance gigs (Fiverr, Upwork, Freelancer, RemoteOK),
        selects a 100% legal & feasible project, decomposes it into milestones,
        distributes to departmental subagents, packages deliverables, credits treasury,
        and pushes changes to GitHub.
        """
        from tools.freelance_harvester import freelance_harvester
        from core.freelance_distributor import freelance_distributor

        target_gig = None
        if job_id:
            target_gig = freelance_harvester.get_job_by_id(job_id)

        if not target_gig:
            gigs = freelance_harvester.fetch_all_platform_gigs()
            for g in gigs:
                if g.get("is_legal") and g.get("is_turnkey_feasible"):
                    target_gig = g
                    break

        if not target_gig:
            return {
                "status": "NO_WORK_AVAILABLE",
                "summary": "No approved legal freelance gigs found meeting 100% turnkey criteria."
            }

        logger.info(f"🚀 Distributing freelance gig '{target_gig['title']}' ({target_gig['platform']}) across subagents...")
        result = freelance_distributor.plan_and_distribute_gig(target_gig, auto_git_sync=True)
        return result

    def sync_with_github(self, commit_message: Optional[str] = None) -> Dict[str, Any]:
        """Manually or autonomously triggers immediate commit & push to GitHub."""
        return git_sync.sync_to_github(commit_message)

    def get_enterprise_overview(self) -> Dict[str, Any]:
        """Provides executive telemetry for dashboard and CLI."""
        telemetry = guardian.get_system_telemetry()
        is_safe, safety_msg = guardian.evaluate_safety()
        q_stats = get_queue_stats()
        depts = get_all_departments()
        subs = get_active_subagents()
        finances = treasury.get_financial_summary()
        from core.database import get_recent_plans
        plans = get_recent_plans(limit=6)
        
        from core.growth_engine import growth_engine
        from core.tunnel_gateway import public_gateway

        return {
            "company": self.company,
            "ceo": self.name,
            "is_running": self.is_running,
            "is_paused": self.is_paused,
            "hardware": {
                **telemetry,
                "is_safe": is_safe,
                "safety_message": safety_msg
            },
            "departments": depts,
            "active_subagents": subs,
            "queue_stats": q_stats,
            "treasury": finances,
            "recent_plans": plans,
            "growth": growth_engine.get_growth_state(),
            "public_gateway": public_gateway.get_gateway_status(),
            "legal_compliance": legal_guardian.get_compliance_metrics(),
            "git_status": git_sync.get_sync_status()
        }

# Global CEO instance
ceo = CEOOrchestrator()

