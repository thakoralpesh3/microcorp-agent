"""
MicroCorp AI - Database Storage Module
SQLite persistence layer for departments, dynamic subagents, tasks, treasury, and metrics.
"""

import json
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import DB_PATH

_lock = threading.Lock()

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False, timeout=30.0)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=15000;")
    except Exception:
        pass
    return conn

def init_db():
    """Initializes the database schema if not present."""
    with _lock:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Departments table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS departments (
                dept_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                head_title TEXT NOT NULL,
                description TEXT,
                icon TEXT,
                status TEXT DEFAULT 'idle',
                is_dynamic INTEGER DEFAULT 0,
                current_subagents_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Subagents table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS subagents (
                subagent_id TEXT PRIMARY KEY,
                dept_id TEXT NOT NULL,
                name TEXT NOT NULL,
                role TEXT NOT NULL,
                status TEXT DEFAULT 'idle',
                assigned_task_id TEXT,
                current_task_title TEXT DEFAULT '',
                progress_percent INTEGER DEFAULT 0,
                current_phase TEXT DEFAULT 'Idle / Ready for sprint',
                started_at TIMESTAMP,
                estimated_duration_seconds INTEGER DEFAULT 45,
                tasks_completed INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_heartbeat TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(dept_id) REFERENCES departments(dept_id)
            )
        """)
        
        # Migrations for existing databases
        for col, col_type in [
            ("current_task_title", "TEXT DEFAULT ''"),
            ("progress_percent", "INTEGER DEFAULT 0"),
            ("current_phase", "TEXT DEFAULT 'Idle / Ready for sprint'"),
            ("started_at", "TIMESTAMP"),
            ("estimated_duration_seconds", "INTEGER DEFAULT 45")
        ]:
            try:
                cursor.execute(f"ALTER TABLE subagents ADD COLUMN {col} {col_type}")
            except Exception:
                pass
        
        # Tasks queue table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY,
                dept_id TEXT NOT NULL,
                title TEXT NOT NULL,
                domain TEXT NOT NULL,
                payload_json TEXT DEFAULT '{}',
                status TEXT DEFAULT 'pending',
                assigned_subagent_id TEXT,
                result_deliverable_path TEXT,
                result_summary TEXT,
                priority INTEGER DEFAULT 5,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            )
        """)
        
        # Treasury ledger table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS treasury_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                title TEXT NOT NULL,
                amount_est_usd REAL DEFAULT 0.0,
                token_cost_usd REAL DEFAULT 0.0,
                deliverable_path TEXT,
                status TEXT DEFAULT 'ready_for_review',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # System metrics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cpu_percent REAL,
                memory_percent REAL,
                battery_percent REAL,
                is_charging INTEGER,
                active_subagents INTEGER,
                queue_depth INTEGER,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Autonomous Work Plans table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS plans (
                plan_id TEXT PRIMARY KEY,
                task_id TEXT,
                title TEXT NOT NULL,
                domain TEXT NOT NULL,
                feasibility_score REAL DEFAULT 1.0,
                feasibility_reasons TEXT,
                plan_json TEXT DEFAULT '{}',
                status TEXT DEFAULT 'planned',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()

# Autonomous Work Plan Operations
def save_plan(plan_id: str, task_id: str, title: str, domain: str, feasibility_score: float, feasibility_reasons: str, plan_dict: Dict[str, Any], status: str = "planned"):
    with _lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO plans (plan_id, task_id, title, domain, feasibility_score, feasibility_reasons, plan_json, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(plan_id) DO UPDATE SET
                task_id=excluded.task_id,
                title=excluded.title,
                domain=excluded.domain,
                feasibility_score=excluded.feasibility_score,
                feasibility_reasons=excluded.feasibility_reasons,
                plan_json=excluded.plan_json,
                status=excluded.status
        """, (plan_id, task_id, title, domain, feasibility_score, feasibility_reasons, json.dumps(plan_dict), status))
        conn.commit()
        conn.close()

def update_plan_status(plan_id: str, status: str):
    with _lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE plans SET status = ? WHERE plan_id = ?", (status, plan_id))
        conn.commit()
        conn.close()

def get_recent_plans(limit: int = 10) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM plans ORDER BY created_at DESC LIMIT ?", (limit,))
    rows = []
    for r in cursor.fetchall():
        d = dict(r)
        d["plan"] = json.loads(d.get("plan_json") or "{}")
        rows.append(d)
    conn.close()
    return rows

# Department Operations
def upsert_department(dept_id: str, name: str, head_title: str, description: str, icon: str, is_dynamic: bool = False, status: str = "idle"):
    with _lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO departments (dept_id, name, head_title, description, icon, is_dynamic, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(dept_id) DO UPDATE SET
                name=excluded.name,
                head_title=excluded.head_title,
                description=excluded.description,
                icon=excluded.icon,
                status=excluded.status
        """, (dept_id, name, head_title, description, icon, 1 if is_dynamic else 0, status))
        conn.commit()
        conn.close()

def update_department_status(dept_id: str, status: str, subagents_count: Optional[int] = None):
    with _lock:
        conn = get_connection()
        cursor = conn.cursor()
        if subagents_count is not None:
            cursor.execute("UPDATE departments SET status = ?, current_subagents_count = ? WHERE dept_id = ?", (status, subagents_count, dept_id))
        else:
            cursor.execute("UPDATE departments SET status = ? WHERE dept_id = ?", (status, dept_id))
        conn.commit()
        conn.close()

def get_all_departments() -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM departments ORDER BY is_dynamic ASC, name ASC")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

# Subagent Operations
def register_subagent(subagent_id: str, dept_id: str, name: str, role: str):
    with _lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO subagents (subagent_id, dept_id, name, role, status, last_heartbeat)
            VALUES (?, ?, ?, ?, 'idle', CURRENT_TIMESTAMP)
        """, (subagent_id, dept_id, name, role))
        # Update department subagent count
        cursor.execute("UPDATE departments SET current_subagents_count = (SELECT count(*) FROM subagents WHERE dept_id = ? AND status != 'terminated') WHERE dept_id = ?", (dept_id, dept_id))
        conn.commit()
        conn.close()

def update_subagent(subagent_id: str, status: str, assigned_task_id: Optional[str] = None, increment_completed: bool = False):
    with _lock:
        conn = get_connection()
        cursor = conn.cursor()
        if increment_completed:
            cursor.execute("""
                UPDATE subagents 
                SET status = ?, assigned_task_id = ?, tasks_completed = tasks_completed + 1, last_heartbeat = CURRENT_TIMESTAMP
                WHERE subagent_id = ?
            """, (status, assigned_task_id, subagent_id))
        else:
            cursor.execute("""
                UPDATE subagents 
                SET status = ?, assigned_task_id = ?, last_heartbeat = CURRENT_TIMESTAMP
                WHERE subagent_id = ?
            """, (status, assigned_task_id, subagent_id))
        conn.commit()
        conn.close()

def terminate_subagent(subagent_id: str):
    with _lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE subagents SET status = 'terminated' WHERE subagent_id = ?", (subagent_id,))
        # Refresh department count
        cursor.execute("""
            UPDATE departments SET current_subagents_count = (
                SELECT count(*) FROM subagents WHERE dept_id = (SELECT dept_id FROM subagents WHERE subagent_id = ?) AND status != 'terminated'
            ) WHERE dept_id = (SELECT dept_id FROM subagents WHERE subagent_id = ?)
        """, (subagent_id, subagent_id))
        conn.commit()
        conn.close()

def get_active_subagents() -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.*, d.name as department_name, d.icon as dept_icon, d.head_title
        FROM subagents s
        LEFT JOIN departments d ON s.dept_id = d.dept_id
        WHERE s.status != 'terminated' 
        ORDER BY s.created_at DESC
    """)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def update_subagent_progress(subagent_id: str, progress_percent: int, phase: str, task_title: Optional[str] = None, estimated_duration: Optional[int] = None):
    with _lock:
        conn = get_connection()
        cursor = conn.cursor()
        if task_title:
            cursor.execute("""
                UPDATE subagents 
                SET progress_percent = ?, current_phase = ?, current_task_title = ?, 
                    started_at = CASE WHEN started_at IS NULL THEN CURRENT_TIMESTAMP ELSE started_at END,
                    estimated_duration_seconds = COALESCE(?, estimated_duration_seconds),
                    last_heartbeat = CURRENT_TIMESTAMP
                WHERE subagent_id = ?
            """, (progress_percent, phase, task_title, estimated_duration, subagent_id))
        else:
            cursor.execute("""
                UPDATE subagents 
                SET progress_percent = ?, current_phase = ?,
                    estimated_duration_seconds = COALESCE(?, estimated_duration_seconds),
                    last_heartbeat = CURRENT_TIMESTAMP
                WHERE subagent_id = ?
            """, (progress_percent, phase, estimated_duration, subagent_id))
        conn.commit()
        conn.close()

def get_subagent_detail(subagent_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.*, d.name as department_name, d.head_title, d.icon as dept_icon,
               t.domain as task_domain, t.payload_json as task_payload, t.status as task_status,
               t.result_deliverable_path, t.created_at as task_created_at
        FROM subagents s
        LEFT JOIN departments d ON s.dept_id = d.dept_id
        LEFT JOIN tasks t ON s.assigned_task_id = t.task_id
        WHERE s.subagent_id = ?
    """, (subagent_id,))
    row = cursor.fetchone()
    if row:
        res = dict(row)
        if res.get("task_payload"):
            try:
                res["task_payload"] = json.loads(res["task_payload"])
            except Exception:
                pass
        conn.close()
        return res
    conn.close()
    return None

# Task Queue Operations
def enqueue_task(task_id: str, dept_id: str, title: str, domain: str, payload: Dict[str, Any], priority: int = 5) -> str:
    with _lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO tasks (task_id, dept_id, title, domain, payload_json, status, priority)
            VALUES (?, ?, ?, ?, ?, 'pending', ?)
            ON CONFLICT(task_id) DO UPDATE SET
                dept_id=excluded.dept_id,
                title=excluded.title,
                domain=excluded.domain,
                payload_json=excluded.payload_json,
                status='pending',
                priority=excluded.priority
        """, (task_id, dept_id, title, domain, json.dumps(payload), priority))
        conn.commit()
        conn.close()
    return task_id

def fetch_pending_task(domain: Optional[str] = None) -> Optional[Dict[str, Any]]:
    with _lock:
        conn = get_connection()
        cursor = conn.cursor()
        if domain:
            cursor.execute("""
                SELECT * FROM tasks 
                WHERE status = 'pending' AND domain = ? 
                ORDER BY priority ASC, created_at ASC 
                LIMIT 1
            """, (domain,))
        else:
            cursor.execute("""
                SELECT * FROM tasks 
                WHERE status = 'pending' 
                ORDER BY priority ASC, created_at ASC 
                LIMIT 1
            """)
        row = cursor.fetchone()
        if row:
            res = dict(row)
            res['payload'] = json.loads(res.get('payload_json') or '{}')
            conn.close()
            return res
        conn.close()
        return None

def complete_task(task_id: str, deliverable_path: str, summary: str):
    with _lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE tasks 
            SET status = 'completed', result_deliverable_path = ?, result_summary = ?, completed_at = CURRENT_TIMESTAMP
            WHERE task_id = ?
        """, (deliverable_path, summary, task_id))
        conn.commit()
        conn.close()

def fail_task(task_id: str, reason: str):
    with _lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE tasks 
            SET status = 'failed', result_summary = ?, completed_at = CURRENT_TIMESTAMP
            WHERE task_id = ?
        """, (reason, task_id))
        conn.commit()
        conn.close()

def get_queue_stats() -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT domain, count(*) as count FROM tasks WHERE status = 'pending' GROUP BY domain")
    by_domain = {r['domain']: r['count'] for r in cursor.fetchall()}
    cursor.execute("SELECT count(*) as total FROM tasks WHERE status = 'pending'")
    total_pending = cursor.fetchone()['total']
    cursor.execute("SELECT count(*) as total FROM tasks WHERE status = 'completed'")
    total_completed = cursor.fetchone()['total']
    conn.close()
    return {
        "total_pending": total_pending,
        "total_completed": total_completed,
        "by_domain": by_domain
    }

def get_recent_tasks(limit: int = 15) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks ORDER BY created_at DESC LIMIT ?", (limit,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

# Treasury Operations
def record_treasury_event(category: str, title: str, amount_est_usd: float, token_cost_usd: float, deliverable_path: str, status: str = "ready_for_review"):
    with _lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO treasury_logs (category, title, amount_est_usd, token_cost_usd, deliverable_path, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (category, title, amount_est_usd, token_cost_usd, deliverable_path, status))
        conn.commit()
        conn.close()

def get_treasury_summary() -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(amount_est_usd) as total_est, SUM(token_cost_usd) as total_costs FROM treasury_logs")
    row = cursor.fetchone()
    total_est = row['total_est'] or 0.0
    total_costs = row['total_costs'] or 0.0
    
    cursor.execute("SELECT * FROM treasury_logs ORDER BY created_at DESC LIMIT 20")
    recent_logs = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {
        "estimated_gross_revenue": round(total_est, 2),
        "total_api_costs": round(total_costs, 4),
        "estimated_net_profit": round(total_est - total_costs, 2),
        "recent_logs": recent_logs
    }

# Metrics Operations
def record_metrics(cpu: float, mem: float, battery: float, charging: bool, active_subagents: int, queue_depth: int):
    with _lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO system_metrics (cpu_percent, memory_percent, battery_percent, is_charging, active_subagents, queue_depth)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (cpu, mem, battery, 1 if charging else 0, active_subagents, queue_depth))
        # Keep metrics table lightweight (last 500 rows)
        cursor.execute("DELETE FROM system_metrics WHERE id NOT IN (SELECT id FROM system_metrics ORDER BY id DESC LIMIT 500)")
        conn.commit()
        conn.close()

# Auto-initialize DB on import
init_db()
