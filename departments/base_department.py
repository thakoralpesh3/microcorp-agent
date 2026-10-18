"""
MicroCorp AI - Base Department & Subagent Class
Abstract foundation for core and dynamic departments in the enterprise.
"""

import uuid
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.database import (
    upsert_department, update_department_status, 
    register_subagent, update_subagent, terminate_subagent,
    complete_task, fail_task
)
from core.treasury import treasury

logger = logging.getLogger("MicroCorp.Department")

class BaseDepartment(ABC):
    def __init__(self, dept_id: str, name: str, head_title: str, description: str, icon: str, is_dynamic: bool = False):
        self.dept_id = dept_id
        self.name = name
        self.head_title = head_title
        self.description = description
        self.icon = icon
        self.is_dynamic = is_dynamic
        self.active_workers: Dict[str, Dict[str, Any]] = {}
        
        # Register in database
        upsert_department(
            dept_id=self.dept_id,
            name=self.name,
            head_title=self.head_title,
            description=self.description,
            icon=self.icon,
            is_dynamic=self.is_dynamic,
            status="idle"
        )
        # Load existing active workers or spawn initial head worker
        from core.database import get_active_subagents
        existing = get_active_subagents()
        for s in existing:
            if s["dept_id"] == self.dept_id:
                self.active_workers[s["subagent_id"]] = {
                    "subagent_id": s["subagent_id"],
                    "name": s["name"],
                    "role": s["role"],
                    "status": s["status"]
                }
        if not self.active_workers:
            self.spawn_worker(role=f"Lead {self.head_title}")

    def spawn_worker(self, role: str) -> str:
        """Spawns and registers a departmental worker subagent."""
        subagent_id = f"{self.dept_id}_sub_{uuid.uuid4().hex[:6]}"
        worker_name = f"{self.name} Worker #{len(self.active_workers) + 1}"
        
        register_subagent(
            subagent_id=subagent_id,
            dept_id=self.dept_id,
            name=worker_name,
            role=role
        )
        self.active_workers[subagent_id] = {
            "subagent_id": subagent_id,
            "name": worker_name,
            "role": role,
            "status": "idle"
        }
        update_department_status(self.dept_id, "active", len(self.active_workers))
        logger.info(f"[{self.name}] Spawned subagent: {worker_name} ({subagent_id})")
        return subagent_id

    def retire_worker(self, subagent_id: str):
        """Retires a departmental worker subagent."""
        if subagent_id in self.active_workers:
            terminate_subagent(subagent_id)
            del self.active_workers[subagent_id]
            status = "active" if self.active_workers else "idle"
            update_department_status(self.dept_id, status, len(self.active_workers))
            logger.info(f"[{self.name}] Retired subagent: {subagent_id}")

    def get_idle_worker(self) -> Optional[str]:
        for sid, info in self.active_workers.items():
            if info["status"] == "idle":
                return sid
        return None

    def execute_task(self, task: Dict[str, Any], subagent_id: Optional[str] = None) -> Dict[str, Any]:
        """Dispatches and tracks task execution on a subagent."""
        from core.database import update_subagent_progress
        worker_id = subagent_id or self.get_idle_worker() or self.spawn_worker(f"{self.name} Dynamic Specialist")
        
        task_id = task["task_id"]
        task_title = task.get("title", "Autonomous Income Deliverable")

        # Defense-in-depth Legal Guardian check
        from core.legal_guardian import legal_guardian
        compliance = legal_guardian.audit_task(task_title, task.get("payload", {}), domain=self.dept_id)
        if not compliance.get("is_legal", True):
            update_subagent(worker_id, "idle")
            update_department_status(self.dept_id, "active", len(self.active_workers))
            logger.error(f"Worker refused illegal task: {compliance['reason']}")
            raise ValueError(f"Legal Guardian Blocked Task: {compliance['reason']}")

        update_subagent(worker_id, "working", assigned_task_id=task_id)
        update_department_status(self.dept_id, "busy", len(self.active_workers))
        
        # Phase 1: Research & Discovery
        update_subagent_progress(
            subagent_id=worker_id,
            progress_percent=20,
            phase="Phase 1: Researching Market Specs & Opportunity Outline",
            task_title=task_title,
            estimated_duration=35
        )
        
        try:
            # Phase 2: Core Engineering & Generation
            update_subagent_progress(
                subagent_id=worker_id,
                progress_percent=55,
                phase="Phase 2: Authoring Production Code & Technical Content"
            )
            result = self.process(task, worker_id)
            
            # Phase 3: Verification & Packaging
            update_subagent_progress(
                subagent_id=worker_id,
                progress_percent=85,
                phase="Phase 3: Verifying Checklist & Packaging Release ZIP"
            )

            # Record in deliverable packager & treasury
            deliverable_path = result.get("deliverable_path", "")
            summary = result.get("summary", "Task completed successfully.")
            prompt_tokens = result.get("prompt_tokens", 1000)
            completion_tokens = result.get("completion_tokens", 2000)
            category = result.get("category", task.get("domain", "digital_product"))
            title = result.get("title", task.get("title", "Autonomous Deliverable"))

            treasury.log_deliverable(
                category=category,
                title=title,
                deliverable_path=deliverable_path,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens
            )

            complete_task(task_id, deliverable_path, summary)

            # If task was derived from an autonomous plan, mark plan completed
            payload = task.get("payload", {})
            plan_id = payload.get("plan_id")
            if plan_id:
                from core.database import update_plan_status
                update_plan_status(plan_id, "completed")

            # Phase 4: Done
            update_subagent_progress(
                subagent_id=worker_id,
                progress_percent=100,
                phase="Delivered to Vault (100% Finished)"
            )
            update_subagent(worker_id, "idle", assigned_task_id=None, increment_completed=True)
            update_department_status(self.dept_id, "active", len(self.active_workers))
            return result

        except Exception as e:
            logger.error(f"[{self.name}] Error executing task {task_id}: {e}")
            fail_task(task_id, str(e))
            update_subagent(worker_id, "idle", assigned_task_id=None)
            update_department_status(self.dept_id, "active", len(self.active_workers))
            raise e

    @abstractmethod
    def process(self, task: Dict[str, Any], subagent_id: str) -> Dict[str, Any]:
        """Domain-specific logic implemented by individual departments."""
        pass
