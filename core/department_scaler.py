"""
MicroCorp AI - Dynamic Department & Subagent Scaler
Monitors workload, auto-scales worker subagents, and dynamically generates new departments on demand.
"""

import time
import logging
from typing import Dict, Any, List, Optional, Type
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    QUEUE_THRESHOLD_FOR_SUBAGENT, 
    MAX_SUBAGENTS_PER_DEPT, 
    MAX_TOTAL_SUBAGENTS, 
    IDLE_TIMEOUT_MINUTES
)
from core.database import (
    get_queue_stats, get_active_subagents, 
    upsert_department, update_department_status
)
from core.resource_guardian import guardian
from departments.base_department import BaseDepartment
from tools.gemini_client import llm_client
from core.legal_guardian import legal_guardian
from tools.packager import packager

logger = logging.getLogger("MicroCorp.DepartmentScaler")

class DynamicDepartment(BaseDepartment):
    """Dynamically generated department created at runtime when workload demands it."""
    def __init__(self, dept_id: str, name: str, head_title: str, description: str, icon: str, system_prompt: str, domain: str):
        self.custom_prompt = system_prompt
        self.domain = domain
        super().__init__(
            dept_id=dept_id,
            name=name,
            head_title=head_title,
            description=description,
            icon=icon,
            is_dynamic=True
        )

    def process(self, task: Dict[str, Any], subagent_id: str) -> Dict[str, Any]:
        payload = task.get("payload", {})
        task_title = task.get("title", f"Specialized {self.domain} Task")
        
        # Match specialized Agency Persona from the 268+ fleet
        from core.agency_agents_manager import agency_agents_manager
        persona = agency_agents_manager.match_agent_for_task(title=task_title, domain=self.domain)
        effective_prompt = agency_agents_manager.build_persona_system_prompt(persona, self.custom_prompt) if persona else self.custom_prompt

        prompt = f"""You are executing a specialized enterprise task for Department '{self.name}'.
Task: {task_title}
Input Context & Payload:
{payload}

Produce a complete, professional, publication-ready deliverable in GitHub Flavored Markdown.
Ensure high structure, actionable depth, and comprehensive execution.
"""
        generated_md, prompt_tokens, candidate_tokens = llm_client.generate(
            prompt=prompt,
            system_instruction=effective_prompt
        )

        pkg = packager.save_deliverable(
            category=self.domain,
            title=task_title,
            markdown_content=generated_md,
            create_zip=False,
            agency_persona=persona
        )

        persona_name = persona.get("name") if persona else subagent_id
        return {
            "title": task_title,
            "category": self.domain,
            "deliverable_path": pkg["primary_path"],
            "summary": f"Completed by dynamic department '{self.name}' ({persona_name}).",
            "prompt_tokens": prompt_tokens,
            "completion_tokens": candidate_tokens,
            "agency_persona": persona.get("name") if persona else None,
            "agency_division": persona.get("division") if persona else None
        }

class DepartmentScaler:
    def __init__(self):
        self.departments: Dict[str, BaseDepartment] = {}

    def register_department(self, dept: BaseDepartment):
        self.departments[dept.dept_id] = dept
        logger.info(f"Registered department: {dept.name} ({dept.dept_id})")

    def get_department_for_domain(self, domain: str) -> Optional[BaseDepartment]:
        domain_mapping = {
            "digital_products": "dept_digital_products",
            "content_newsletter": "dept_content_newsletter",
            "gig_proposal": "dept_gig_proposal",
            "intelligence": "dept_intelligence"
        }
        dept_id = domain_mapping.get(domain)
        if dept_id and dept_id in self.departments:
            return self.departments[dept_id]
        
        # Check dynamic departments
        for dept in self.departments.values():
            if getattr(dept, "domain", None) == domain:
                return dept
        return None

    def create_dynamic_department(self, domain: str, name_hint: Optional[str] = None) -> BaseDepartment:
        """Dynamically spawns a brand new department at runtime to handle new domains or high overflow."""
        # 0. Strict Legality Screening on Domain
        audit = legal_guardian.audit_task(domain, name_hint or "")
        if not audit["is_legal"]:
            logger.warning(f"⚖️ Dynamic department rejected by Legal Guardian: domain='{domain}' [{audit['risk_category']}]")
            raise ValueError(f"Prohibited domain '{domain}': {audit['reason']}")

        dept_id = f"dept_dynamic_{domain.lower().replace(' ', '_')}"
        
        if dept_id in self.departments:
            return self.departments[dept_id]

        from core.agency_agents_manager import agency_agents_manager
        agency_div = agency_agents_manager.get_divisions().get(domain.lower().replace("_", "-"))
        if agency_div:
            clean_name = name_hint or f"{agency_div['name']} Division"
            head_title = f"{agency_div['name']} Principal Lead"
            description = f"Autonomous enterprise division powered by The Agency ({agency_div['agent_count']} specialized agents). {agency_div['description']}"
            icon = "fa-robot text-primary"
            system_prompt = f"""You are the Lead Coordinator for the {clean_name} at MicroCorp AI.
Powered by The Agency's specialized personas.
Domain focus: {domain}. Execute autonomous tasks with rigorous quality and production standards."""
        else:
            clean_name = name_hint or f"{domain.replace('_', ' ').title()} Operations"
            head_title = f"{domain.replace('_', ' ').title()} Commander"
            description = f"Autonomous on-demand department dynamically generated to handle high-volume {domain} tasks."
            icon = "fa-cubes-stacked text-purple"
            system_prompt = f"""You are the head of the {clean_name} department at MicroCorp AI.
Your focus is autonomous execution of {domain} deliverables with extreme attention to detail,
commercial value, and rapid turnaround."""

        dynamic_dept = DynamicDepartment(
            dept_id=dept_id,
            name=clean_name,
            head_title=head_title,
            description=description,
            icon=icon,
            system_prompt=system_prompt,
            domain=domain
        )
        self.register_department(dynamic_dept)
        logger.info(f"🔥 DYNAMICALLY GENERATED NEW DEPARTMENT: {clean_name} ({dept_id})")
        return dynamic_dept

    def check_and_scale_workload(self) -> Dict[str, Any]:
        """
        Evaluates queue load vs laptop capacity and scales subagents or departments up/down.
        """
        stats = get_queue_stats()
        active_subagents = get_active_subagents()
        total_active_subagents = len(active_subagents)
        is_safe, reason = guardian.evaluate_safety()

        actions_taken = []

        # 1. If laptop is under heavy load or battery is low, don't spawn new subagents
        if not is_safe:
            logger.warning(f"Scaling restricted by Resource Guardian: {reason}")
            return {
                "scaled": False,
                "reason": reason,
                "active_subagents": total_active_subagents,
                "queue_stats": stats
            }

        # 2. Check pending tasks by domain
        for domain, pending_count in stats["by_domain"].items():
            dept = self.get_department_for_domain(domain)
            
            # If no existing department handles this domain, dynamically generate one!
            if not dept:
                logger.info(f"Unserviced domain detected with {pending_count} pending tasks: {domain}. Spawning dynamic department...")
                dept = self.create_dynamic_department(domain)
                actions_taken.append(f"Spawned new dynamic department: {dept.name}")

            # Check if this department's load requires more worker subagents
            current_dept_workers = len(dept.active_workers)
            if pending_count >= QUEUE_THRESHOLD_FOR_SUBAGENT:
                if current_dept_workers < MAX_SUBAGENTS_PER_DEPT and total_active_subagents < MAX_TOTAL_SUBAGENTS:
                    worker_id = dept.spawn_worker(role=f"High-Throughput {domain.title()} Specialist")
                    total_active_subagents += 1
                    actions_taken.append(f"[{dept.name}] Spawns subagent {worker_id} (Load: {pending_count} pending)")
                    logger.info(f"🚀 Scaling UP: [{dept.name}] spawned subagent {worker_id} to handle {pending_count} pending tasks.")

        # 3. Graceful down-scaling: retire idle workers if queue is empty
        for dept in list(self.departments.values()):
            # Keep at least 1 lead worker per core department
            if len(dept.active_workers) > 1:
                domain_key = getattr(dept, "domain", dept.dept_id.replace("dept_", ""))
                pending_for_dept = stats["by_domain"].get(domain_key, 0)
                if pending_for_dept == 0:
                    # Find idle worker to retire
                    for sid, winfo in list(dept.active_workers.items()):
                        if winfo["status"] == "idle" and len(dept.active_workers) > 1:
                            dept.retire_worker(sid)
                            actions_taken.append(f"[{dept.name}] Retired idle subagent {sid}")
                            break

        return {
            "scaled": bool(actions_taken),
            "actions": actions_taken,
            "active_subagents": total_active_subagents,
            "queue_stats": stats
        }

scaler = DepartmentScaler()
