"""
MicroCorp AI - Main Application Server & CLI Entrypoint
FastAPI web dashboard + Autonomous background CEO runner.
"""

import os
import sys
import argparse
import uvicorn
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, Dict, Any

# Ensure import paths are clean
BASE_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(BASE_DIR))

from config import SERVER_HOST, SERVER_PORT, DELIVERABLES_DIR, STATIC_DIR, COMPANY_NAME, CEO_NAME
from core.ceo_orchestrator import ceo
from tools.gemini_client import llm_client

@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"🚀 Initializing {COMPANY_NAME} under command of {CEO_NAME}...")
    ceo.start()
    yield
    print(f"🛑 Gracefully stopping {COMPANY_NAME}...")
    ceo.stop()

app = FastAPI(
    title=COMPANY_NAME,
    description="Autonomous Laptop Enterprise with Dynamic Department & Subagent Scaling",
    lifespan=lifespan
)

# Mount Static Files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

class SprintRequest(BaseModel):
    domain: str
    title: str
    payload: Optional[Dict[str, Any]] = None

class ApiKeyUpdate(BaseModel):
    api_key: str

class CustomerOrderRequest(BaseModel):
    customer_name: Optional[str] = "Client"
    customer_email: Optional[str] = ""
    project_title: str
    project_requirements: str
    budget_usd: Optional[float] = 0.0

@app.get("/", response_class=HTMLResponse)
async def read_root():
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="Dashboard UI not found.")
    with open(index_file, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.get("/api/telemetry")
async def get_telemetry():
    return ceo.get_enterprise_overview()

@app.post("/api/sprint")
async def trigger_sprint(req: SprintRequest):
    try:
        task_id = ceo.trigger_sprint(
            domain=req.domain,
            custom_title=req.title,
            payload=req.payload or {}
        )
        return {"status": "enqueued", "task_id": task_id, "domain": req.domain, "title": req.title}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/compliance")
async def get_compliance_endpoint():
    from core.legal_guardian import legal_guardian
    return legal_guardian.get_compliance_metrics()

@app.post("/api/customer/order")
async def submit_customer_order(req: CustomerOrderRequest):
    from core.legal_guardian import legal_guardian
    audit = legal_guardian.audit_customer_order(
        project_title=req.project_title,
        requirements=req.project_requirements,
        client_name=req.customer_name,
        client_email=req.customer_email
    )

    if not audit.get("is_legal", True):
        # Save customer refusal document to deliverables vault so it is accessible
        from tools.packager import packager
        rejection_pkg = packager.save_deliverable(
            category="freelance_proposal",
            title=f"Customer Refusal - {req.project_title}",
            markdown_content=audit["rejection_notice_md"],
            create_zip=False
        )
        return {
            "status": "REJECTED_UNLAWFUL",
            "verdict": "REJECTED",
            "project_title": req.project_title,
            "risk_category": audit["risk_category"],
            "reason": audit["reason"],
            "legal_statute": audit["legal_statute"],
            "rejection_notice": audit["rejection_notice_md"],
            "advisory_summary": audit["advisory_summary"],
            "rejection_document_path": rejection_pkg["primary_path"]
        }

    # Lawful customer project: enqueue as high-priority proposal & implementation task
    task_id = ceo.trigger_sprint(
        domain="gig_proposal",
        custom_title=f"Customer Order: {req.project_title}",
        payload={
            "job_title": req.project_title,
            "job_description": req.project_requirements,
            "client_name": req.customer_name,
            "budget": req.budget_usd
        }
    )
    return {
        "status": "ACCEPTED_LAWFUL",
        "verdict": "ACCEPTED",
        "task_id": task_id,
        "project_title": req.project_title,
        "message": "Customer order accepted and verified 100% compliant with legal and ethical policies. Enqueued for execution."
    }

@app.post("/api/toggle_pause")
async def toggle_pause():
    ceo.is_paused = not ceo.is_paused
    return {"is_paused": ceo.is_paused}

@app.post("/api/settings/key")
async def update_api_key(req: ApiKeyUpdate):
    llm_client.set_api_key(req.api_key)
    return {"status": "updated"}

@app.get("/api/terms")
async def get_terms_json():
    terms_file = BASE_DIR / "TERMS_AND_CONDITIONS.md"
    if not terms_file.exists():
        return {"terms": "Terms and conditions document not found."}
    return {"terms": terms_file.read_text(encoding="utf-8")}

@app.get("/terms", response_class=HTMLResponse)
async def get_terms_html():
    from tools.packager import simple_markdown_to_html
    terms_file = BASE_DIR / "TERMS_AND_CONDITIONS.md"
    md_content = terms_file.read_text(encoding="utf-8") if terms_file.exists() else "# Terms and Conditions Not Found"
    html_body = simple_markdown_to_html(md_content)
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>MicroCorp AI - Terms and Conditions</title>
    <link rel="stylesheet" href="/static/css/style.css">
    <style>
        body {{ max-width: 900px; margin: 40px auto; line-height: 1.7; padding: 20px; }}
        .terms-box {{ background: rgba(18, 24, 38, 0.9); padding: 40px; border-radius: 12px; border: 1px solid var(--card-border); }}
        h1, h2, h3 {{ color: #60a5fa; margin-top: 24px; }}
        hr {{ border: 0; border-top: 1px solid rgba(255,255,255,0.1); margin: 20px 0; }}
        a {{ color: #60a5fa; text-decoration: none; }}
    </style>
</head>
<body>
    <div style="margin-bottom: 20px;">
        <a href="/" class="btn-action" style="display: inline-flex;"><i class="fa-solid fa-arrow-left"></i> Back to Console</a>
    </div>
    <div class="terms-box">
        {html_body}
    </div>
</body>
</html>"""
    return HTMLResponse(content=html)

@app.post("/api/autonomous_cycle")
async def trigger_autonomous_cycle():
    ceo.run_autonomous_income_cycle()
    return {"status": "autonomous_cycle_dispatched"}

@app.get("/api/subagent/{subagent_id}")
async def get_subagent_endpoint(subagent_id: str):
    from core.database import get_subagent_detail
    detail = get_subagent_detail(subagent_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Subagent not found.")
    return detail

@app.get("/api/freelance/jobs")
async def get_freelance_jobs():
    from tools.freelance_harvester import freelance_harvester
    return freelance_harvester.fetch_all_platform_gigs()

class FreelanceDistributeRequest(BaseModel):
    job_id: Optional[str] = None
    platform: Optional[str] = "Fiverr"
    title: Optional[str] = None
    description: Optional[str] = None
    budget: Optional[float] = 200.0
    client_name: Optional[str] = "Client"

@app.post("/api/freelance/distribute")
async def distribute_freelance_work(req: Optional[FreelanceDistributeRequest] = None):
    import uuid
    from tools.freelance_harvester import freelance_harvester
    from core.freelance_distributor import freelance_distributor

    target_job = None
    if req and req.job_id:
        target_job = freelance_harvester.get_job_by_id(req.job_id)

    if not target_job and req and req.title:
        target_job = {
            "job_id": f"custom_{uuid.uuid4().hex[:8]}",
            "platform": req.platform or "Fiverr",
            "title": req.title,
            "description": req.description or "",
            "budget": req.budget or 200.0,
            "client_name": req.client_name or "Client"
        }

    if not target_job:
        gigs = freelance_harvester.fetch_all_platform_gigs()
        approved = [g for g in gigs if g.get("is_legal") and g.get("is_turnkey_feasible")]
        if not approved:
            raise HTTPException(status_code=404, detail="No approved turnkey freelance gigs found.")
        target_job = approved[0]

    result = freelance_distributor.plan_and_distribute_gig(target_job, auto_git_sync=True)
    return result

class GitSyncRequest(BaseModel):
    commit_message: Optional[str] = None

@app.get("/api/git/status")
async def get_git_status():
    from core.git_sync import git_sync
    return git_sync.get_sync_status()

@app.post("/api/git/sync")
async def trigger_git_sync(req: Optional[GitSyncRequest] = None):
    from core.git_sync import git_sync
    msg = req.commit_message if req else None
    return git_sync.sync_to_github(msg)

@app.get("/api/plans")
async def get_plans_api():
    from core.database import get_recent_plans
    return get_recent_plans(limit=10)

@app.get("/view_plan/{plan_id}", response_class=HTMLResponse)
async def view_plan_html(plan_id: str):
    from tools.packager import simple_markdown_to_html
    plan_file = DELIVERABLES_DIR / "plans" / f"{plan_id}.md"
    if not plan_file.exists():
        raise HTTPException(status_code=404, detail="Plan document not found.")
    md_content = plan_file.read_text(encoding="utf-8")
    html_body = simple_markdown_to_html(md_content)
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Autonomous Plan: {plan_id}</title>
    <link rel="stylesheet" href="/static/css/style.css">
    <style>
        body {{ max-width: 900px; margin: 40px auto; line-height: 1.7; padding: 20px; }}
        .plan-box {{ background: rgba(18, 24, 38, 0.95); padding: 40px; border-radius: 12px; border: 1px solid var(--card-border); }}
        h1 {{ color: #60a5fa; font-size: 26px; border-bottom: 2px solid #3b82f6; padding-bottom: 12px; }}
        h2 {{ color: #93c5fd; margin-top: 24px; border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 8px; }}
        h3 {{ color: #c084fc; margin-top: 18px; }}
        ul {{ padding-left: 20px; }}
        li {{ margin-bottom: 6px; }}
        a {{ color: #60a5fa; text-decoration: none; }}
    </style>
</head>
<body>
    <div style="margin-bottom: 20px;">
        <a href="/" class="btn-action" style="display: inline-flex;"><i class="fa-solid fa-arrow-left"></i> Back to Console</a>
    </div>
    <div class="plan-box">
        {html_body}
    </div>
</body>
</html>"""
    return HTMLResponse(content=html)

@app.get("/view_deliverable/{file_path:path}")
async def view_deliverable(file_path: str):
    target = DELIVERABLES_DIR / file_path
    if not target.exists():
        raise HTTPException(status_code=404, detail="Deliverable file not found.")
    
    if target.suffix.lower() == ".html":
        return FileResponse(path=str(target), media_type="text/html")
    elif target.suffix.lower() in [".md", ".txt"]:
        return FileResponse(path=str(target), media_type="text/markdown")
    elif target.suffix.lower() == ".zip":
        return FileResponse(path=str(target), media_type="application/zip", filename=target.name)
    return FileResponse(path=str(target))

def main():
    parser = argparse.ArgumentParser(description="MicroCorp AI Enterprise Launcher")
    parser.add_argument("--port", type=int, default=SERVER_PORT, help="Port to run the dashboard on")
    parser.add_argument("--host", type=str, default=SERVER_HOST, help="Host to bind the server")
    args = parser.parse_args()

    print("=" * 65)
    print(f"  🏢 {COMPANY_NAME.upper()} - AUTONOMOUS LAPTOP ENTERPRISE")
    print(f"  👑 Executive Core: {CEO_NAME}")
    print(f"  🌐 Dashboard: http://{args.host}:{args.port}")
    print("=" * 65)

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")

if __name__ == "__main__":
    main()
