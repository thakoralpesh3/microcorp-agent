"""
MicroCorp AI - Main Application Server & CLI Entrypoint
FastAPI web dashboard + Autonomous background CEO runner.
"""

import os
import re
import sys
import uuid
import argparse
import uvicorn
from pathlib import Path
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, Response
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

class TrackOrderRequest(BaseModel):
    query: str

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
    budget_val = req.budget_usd if (req.budget_usd and req.budget_usd > 0) else 50.0
    budget_inr = round(budget_val * 86.5)
    task_id = ceo.trigger_sprint(
        domain="gig_proposal",
        custom_title=f"Customer Order: {req.project_title}",
        payload={
            "job_title": req.project_title,
            "job_description": req.project_requirements,
            "client_name": req.customer_name,
            "budget": budget_val
        }
    )
    from core.upi_payment import upi_gateway
    upi_uri = upi_gateway.generate_upi_uri(amount_inr=budget_inr, note=f"Order {task_id[:8]}")
    return {
        "status": "ACCEPTED_LAWFUL",
        "verdict": "ACCEPTED",
        "task_id": task_id,
        "project_title": req.project_title,
        "amount_usd": budget_val,
        "amount_inr": budget_inr,
        "payout_upi_id": upi_gateway.upi_id,
        "payee_name": upi_gateway.payee_name,
        "upi_uri": upi_uri,
        "message": "Customer order accepted and verified 100% compliant with legal and ethical policies. Enqueued for execution."
    }

@app.post("/api/customer/track")
async def track_customer_order(req: TrackOrderRequest):
    q = req.query.strip().lower()
    if not q:
        raise HTTPException(status_code=400, detail="Please enter a UTR number, Order ID, or keyword.")
    
    from core.upi_payment import upi_gateway
    # 1. Search verified transactions list
    for tx in upi_gateway.transactions:
        if tx.get("utr_number", "").lower() == q or tx.get("order_id", "").lower() == q:
            title = tx.get("asset_title", "Purchased Deliverable")
            return {
                "found": True,
                "status": "PAID_VERIFIED",
                "asset_id": tx.get("order_id"),
                "amount_inr": tx.get("amount_inr"),
                "download_url": "/store",
                "message": f"Payment verified ({tx.get('utr_number')})! Your order '{title}' is confirmed and active."
            }

    # 2. Search deliverables directory for keyword matches
    ready_dir = DELIVERABLES_DIR / "ready_to_monetize"
    matches = list(ready_dir.glob(f"*{q}*.zip")) if ready_dir.exists() else []
    if not matches and DELIVERABLES_DIR.exists():
        matches = list(DELIVERABLES_DIR.rglob(f"*{q}*.zip"))

    if matches:
        zip_p = matches[0]
        slug = zip_p.stem
        return {
            "found": True,
            "status": "READY_FOR_DELIVERY",
            "asset_id": slug,
            "download_url": f"/view_deliverable/ready_to_monetize/{zip_p.name}?download=true",
            "preview_url": f"/view_deliverable/ready_to_monetize/{slug}.html",
            "message": f"Found matching turnkey deliverable package: {slug.replace('_', ' ').title()}"
        }

    return {
        "found": False,
        "message": "No matching order or verified UTR found. If you just made a UPI payment, please allow 1-2 minutes or contact Alpesh Thakor at talpesh100@ybl."
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
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MicroCorp AI - Master Terms of Service & Legal Disclaimer</title>
    <link rel="stylesheet" href="/static/css/style.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <style>
        body {{ max-width: 960px; margin: 30px auto; line-height: 1.8; padding: 20px; color: #cbd5e1; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }}
        .terms-box {{ background: rgba(18, 24, 38, 0.95); padding: 42px; border-radius: 14px; border: 1px solid var(--card-border); box-shadow: 0 10px 30px rgba(0,0,0,0.5); }}
        h1 {{ color: #f8fafc; font-size: 26px; border-bottom: 2px solid rgba(59, 130, 246, 0.4); padding-bottom: 12px; margin-top: 0; }}
        h2 {{ color: #60a5fa; font-size: 19px; margin-top: 32px; border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 8px; }}
        h3 {{ color: #93c5fd; font-size: 16px; margin-top: 20px; }}
        blockquote {{ background: rgba(239, 68, 68, 0.1); border-left: 4px solid #ef4444; padding: 16px 20px; border-radius: 6px; margin: 20px 0; color: #fca5a5; }}
        hr {{ border: 0; border-top: 1px solid rgba(255,255,255,0.1); margin: 26px 0; }}
        a {{ color: #60a5fa; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        code {{ background: rgba(0,0,0,0.4); padding: 2px 6px; border-radius: 4px; font-family: monospace; color: #34d399; font-size: 13px; }}
        ul, ol {{ padding-left: 24px; }}
        li {{ margin-bottom: 8px; }}
        strong {{ color: #f1f5f9; }}
    </style>
</head>
<body>
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; flex-wrap: wrap; gap: 10px;">
        <div style="display: flex; gap: 10px;">
            <a href="/store" class="btn-action" style="display: inline-flex;"><i class="fa-solid fa-arrow-left"></i> Digital Store</a>
            <a href="/" class="btn-action" style="display: inline-flex;"><i class="fa-solid fa-gauge"></i> Console</a>
        </div>
        <div style="background: rgba(16, 185, 129, 0.15); border: 1px solid rgba(16, 185, 129, 0.3); color: #34d399; padding: 6px 14px; border-radius: 999px; font-size: 13px; font-weight: 600;">
            <i class="fa-solid fa-shield-halved"></i> Governing Law: Republic of India (Ahmedabad)
        </div>
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
async def view_deliverable(file_path: str, download: bool = False, format: Optional[str] = None):
    # 1. Resolve path - exact, clean relative, or recursive search
    target = DELIVERABLES_DIR / file_path
    if not target.exists():
        clean_p = file_path.lstrip("/").replace("deliverables/", "", 1)
        target = DELIVERABLES_DIR / clean_p
        
    if not target.exists():
        fname = Path(file_path).name
        matches = list(DELIVERABLES_DIR.rglob(fname))
        if matches:
            target = matches[0]
        else:
            base_stem = Path(file_path).stem
            html_matches = list(DELIVERABLES_DIR.rglob(f"{base_stem}.html"))
            if html_matches:
                target = html_matches[0]
            else:
                zip_matches = list(DELIVERABLES_DIR.rglob(f"{base_stem}.zip"))
                if zip_matches:
                    target = zip_matches[0]

    if not target or not target.exists():
        raise HTTPException(status_code=404, detail="Deliverable file not found.")

    # 2. Direct download request
    if download:
        media_type = "application/zip" if target.suffix.lower() == ".zip" else "application/octet-stream"
        return FileResponse(path=str(target), media_type=media_type, filename=target.name)

    # 3. Handle ZIP archives accessed via browser navigation -> Show HTML preview
    if target.suffix.lower() == ".zip":
        # Sibling START_HERE.html check (highest priority customer onboarding)
        start_sibling = target.parent / f"{target.stem}_START_HERE.html"
        if start_sibling.exists():
            return FileResponse(path=str(start_sibling), media_type="text/html")

        # Sibling HTML check
        html_sibling = target.with_suffix(".html")
        if html_sibling.exists():
            return FileResponse(path=str(html_sibling), media_type="text/html")
        
        # Sibling HTML anywhere in deliverables
        sibling_matches = list(DELIVERABLES_DIR.rglob(f"{target.stem}_START_HERE.html")) or list(DELIVERABLES_DIR.rglob(f"{target.stem}.html"))
        if sibling_matches:
            return FileResponse(path=str(sibling_matches[0]), media_type="text/html")

        # Inspect inside the ZIP archive for START_HERE.html or index.html or README.md
        try:
            import zipfile
            with zipfile.ZipFile(target, "r") as zf:
                start_names = [n for n in zf.namelist() if n.lower().endswith("start_here.html")]
                if start_names:
                    content = zf.read(start_names[0]).decode("utf-8", errors="replace")
                    return HTMLResponse(content=content)
                html_names = [n for n in zf.namelist() if n.lower().endswith(".html")]
                if html_names:
                    content = zf.read(html_names[0]).decode("utf-8", errors="replace")
                    return HTMLResponse(content=content)
                md_names = [n for n in zf.namelist() if n.lower().endswith(".md")]
                if md_names:
                    md_text = zf.read(md_names[0]).decode("utf-8", errors="replace")
                    from tools.packager import simple_markdown_to_html
                    html_body = simple_markdown_to_html(md_text)
                    rendered = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>{target.stem}</title>
                    <style>body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; max-width: 860px; margin: 40px auto; padding: 20px; line-height: 1.6; color: #1e293b; background: #f8fafc; }} .box {{ background: #fff; padding: 36px 44px; border-radius: 12px; border: 1px solid #e2e8f0; }} pre {{ background: #0f172a; color: #f8fafc; padding: 16px; border-radius: 8px; overflow-x: auto; }}</style>
                    </head><body><div class="box">{html_body}</div></body></html>"""
                    return HTMLResponse(content=rendered)
        except Exception:
            pass
        return FileResponse(path=str(target), media_type="application/zip", filename=target.name)

    # 4. Handle HTML previews
    if target.suffix.lower() == ".html":
        return FileResponse(path=str(target), media_type="text/html")

    # 5. Handle Markdown & text files: render formatted HTML in browser
    if target.suffix.lower() in [".md", ".txt"]:
        if format == "raw":
            return FileResponse(path=str(target), media_type="text/markdown")
        try:
            from tools.packager import simple_markdown_to_html
            text_content = target.read_text(encoding="utf-8", errors="replace")
            html_body = simple_markdown_to_html(text_content)
            rendered = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{target.name}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; max-width: 860px; margin: 40px auto; padding: 20px; line-height: 1.6; color: #1e293b; background: #f8fafc; }}
        .box {{ background: #ffffff; padding: 36px 44px; border-radius: 12px; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }}
        pre {{ background: #0f172a; color: #f8fafc; padding: 16px; border-radius: 8px; overflow-x: auto; }}
        code {{ background: #f1f5f9; padding: 2px 6px; border-radius: 4px; font-family: monospace; }}
        pre code {{ background: transparent; color: inherit; }}
        h1, h2, h3 {{ color: #0f172a; }}
        hr {{ border: 0; border-top: 1px solid #e2e8f0; margin: 24px 0; }}
        a {{ color: #2563eb; text-decoration: none; }}
    </style>
</head>
<body>
    <div style="margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center;">
        <a href="/" style="color: #2563eb; text-decoration: none; font-size: 14px; font-weight: 600;">← Back to Console</a>
        <a href="/view_deliverable/{file_path}?download=true" style="background: #2563eb; color: #fff; padding: 6px 12px; border-radius: 6px; font-size: 13px; font-weight: 600;">Download Source</a>
    </div>
    <div class="box">
        {html_body}
    </div>
</body>
</html>"""
            return HTMLResponse(content=rendered)
        except Exception:
            return FileResponse(path=str(target), media_type="text/markdown")

    return FileResponse(path=str(target))

# ==========================================
# Real Passive Income: Storefront & UPI Checkout
# ==========================================

class UTRVerificationRequest(BaseModel):
    order_id: str
    utr_number: str
    amount_inr: float
    asset_id: str
    customer_email: Optional[str] = ""

@app.get("/api/payout/config")
async def get_payout_config():
    from core.upi_payment import upi_gateway
    return upi_gateway.get_payment_summary()

@app.post("/api/payment/verify")
async def verify_payment_endpoint(req: UTRVerificationRequest):
    from core.upi_payment import upi_gateway
    res = upi_gateway.verify_utr_payment(
        order_id=req.order_id,
        utr_number=req.utr_number,
        amount_inr=req.amount_inr,
        customer_email=req.customer_email,
        asset_title=req.asset_id.replace("_", " ").title()
    )
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error"))
    return {
        **res,
        "download_url": f"/download_purchased/{req.asset_id}"
    }

@app.get("/download_purchased/{asset_id}")
async def download_purchased_asset(asset_id: str):
    # Find zip file matching asset_id
    matches = list(DELIVERABLES_DIR.glob(f"**/*{asset_id}*.zip"))
    if not matches:
        raise HTTPException(status_code=404, detail="Purchased asset archive not found.")
    target_zip = matches[0]
    return FileResponse(path=str(target_zip), media_type="application/zip", filename=target_zip.name)

@app.get("/api/gateway/public_url")
async def get_gateway_public_url():
    from core.tunnel_gateway import public_gateway
    return public_gateway.get_gateway_status()

@app.get("/api/gateway/qr.svg")
async def get_gateway_qr_svg():
    from config import PUBLIC_QR_FILE
    if PUBLIC_QR_FILE.exists():
        return FileResponse(path=str(PUBLIC_QR_FILE), media_type="image/svg+xml")
    raise HTTPException(status_code=404, detail="Public mobile QR code not yet generated.")

@app.get("/api/growth/metrics")
async def get_growth_metrics():
    from core.growth_engine import growth_engine
    return growth_engine.get_growth_state()

STORE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MicroCorp AI - Official Commercial Digital Storefront</title>
    <meta name="description" content="MicroCorp AI Official Storefront: Over 170+ production developer toolkits, architecture blueprints, cheatsheets, and prompt engineering systems with instant UPI delivery to talpesh100@ybl.">
    <meta name="keywords" content="developer tools, python cheatsheets, architecture guides, prompt packs, micro-saas boilerplates, upi digital product">
    <!-- OpenGraph Social Sharing Meta Tags -->
    <meta property="og:title" content="MicroCorp AI - Commercial Developer Toolkits & Digital Blueprints">
    <meta property="og:description" content="Battle-tested production kits, cheatsheets, and architecture boilerplates. Instant UPI checkout (PhonePe, GPay, Paytm) to talpesh100@ybl.">
    <meta property="og:type" content="website">
    <meta property="og:url" content="/store">
    <!-- Twitter Cards -->
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="MicroCorp AI - Commercial Developer Toolkits">
    <meta name="twitter:description" content="Battle-tested production kits, cheatsheets, and boilerplates with instant UPI download.">
    <!-- Schema.org JSON-LD Structured Data for Google/Bing Indexing -->
    <script type="application/ld+json">
    {
      "@context": "https://schema.org",
      "@type": "WebSite",
      "name": "MicroCorp AI Storefront",
      "url": "/store",
      "description": "Commercial developer toolkits, architectural blueprints, and cheatsheets with instant UPI download.",
      "publisher": {
        "@type": "Organization",
        "name": "MicroCorp AI Enterprise",
        "founder": "Alpesh Thakor"
      }
    }
    </script>
    <link rel="stylesheet" href="/static/css/style.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <style>
        body { max-width: 1100px; margin: 30px auto; padding: 20px; }
        .hero { background: linear-gradient(135deg, rgba(30, 41, 59, 0.9), rgba(15, 23, 42, 0.95)); border: 1px solid var(--card-border); padding: 36px; border-radius: 16px; margin-bottom: 24px; }
        .payout-tag { background: rgba(16, 185, 129, 0.15); border: 1px solid rgba(16, 185, 129, 0.3); color: #34d399; padding: 6px 14px; border-radius: 999px; font-size: 13px; font-weight: 600; display: inline-flex; align-items: center; gap: 8px; }
        .cat-btn { background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.12); color: #94a3b8; padding: 8px 16px; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; transition: all 0.2s; }
        .cat-btn:hover, .cat-btn.active { background: rgba(59, 130, 246, 0.2); border-color: #3b82f6; color: #60a5fa; }
        .search-box { width: 100%; box-sizing: border-box; background: rgba(18, 24, 38, 0.95); border: 1px solid var(--card-border); color: #f8fafc; padding: 14px 18px; border-radius: 12px; font-size: 14px; outline: none; transition: border-color 0.2s; }
        .search-box:focus { border-color: #3b82f6; }
    </style>
</head>
<body>
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; flex-wrap: wrap; gap: 10px;">
        <div style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap;">
            <a href="/" class="btn-action" style="display: inline-flex; text-decoration: none;"><i class="fa-solid fa-arrow-left"></i> Console</a>
            <a href="/hire" class="btn-action purple" style="display: inline-flex; align-items: center; gap: 6px; text-decoration: none; font-weight: 700;">
                <i class="fa-solid fa-briefcase"></i> Hire AI Agent (Custom Work)
            </a>
            <button onclick="openTrackModal()" class="btn-action" style="display: inline-flex; align-items: center; gap: 6px; cursor: pointer; border: 1px solid rgba(255,255,255,0.15); background: rgba(255,255,255,0.05); color: #cbd5e1;">
                <i class="fa-solid fa-magnifying-glass"></i> Track by UTR
            </button>
            <a href="https://wa.me/919999999999?text=Hi%20Alpesh,%20I%20am%20interested%20in%20MicroCorp%20AI%20custom%20projects" target="_blank" class="btn-action" style="display: inline-flex; align-items: center; gap: 6px; text-decoration: none; background: rgba(37, 211, 102, 0.15); border: 1px solid rgba(37, 211, 102, 0.3); color: #4ade80;">
                <i class="fa-brands fa-whatsapp"></i> WhatsApp Reach
            </a>
        </div>
        <div class="payout-tag">
            <i class="fa-solid fa-circle-check"></i> Official Payout: <strong>__PAYOUT_UPI_ID__</strong> (__PAYEE_NAME__)
        </div>
    </div>

    <div class="hero">
        <span class="badge-tag" style="background: rgba(139, 92, 246, 0.2); color: #c084fc; margin-bottom: 12px; display: inline-block;">MICROCORP AI ENTERPRISE STOREFRONT</span>
        <h1 style="color: #f8fafc; font-size: 32px; margin: 6px 0 12px 0;">Commercial Developer Toolkits & Digital Products</h1>
        <p style="color: #94a3b8; font-size: 15px; max-width: 750px; line-height: 1.6;">
            Battle-tested architecture cheatsheets, automated prompt engineering packs, and micro-SaaS boilerplates.
            Purchase directly with zero intermediary fees using any Indian UPI app (PhonePe, Google Pay, Paytm, BHIM).
        </p>
        <div style="display: flex; gap: 10px; flex-wrap: wrap; margin-top: 16px;">
            <span style="background: rgba(59, 130, 246, 0.15); border: 1px solid rgba(59, 130, 246, 0.3); color: #60a5fa; font-size: 12px; font-weight: 600; padding: 4px 10px; border-radius: 6px;"><i class="fa-solid fa-code"></i> Cheatsheets: ₹399</span>
            <span style="background: rgba(245, 158, 11, 0.15); border: 1px solid rgba(245, 158, 11, 0.3); color: #fbbf24; font-size: 12px; font-weight: 600; padding: 4px 10px; border-radius: 6px;"><i class="fa-solid fa-book-open"></i> Research: ₹799</span>
            <span style="background: rgba(16, 185, 129, 0.15); border: 1px solid rgba(16, 185, 129, 0.3); color: #34d399; font-size: 12px; font-weight: 600; padding: 4px 10px; border-radius: 6px;"><i class="fa-solid fa-cubes"></i> Toolkits: ₹1,799</span>
            <span style="background: rgba(168, 85, 247, 0.15); border: 1px solid rgba(168, 85, 247, 0.3); color: #c084fc; font-size: 12px; font-weight: 600; padding: 4px 10px; border-radius: 6px;"><i class="fa-solid fa-layer-group"></i> Enterprise: ₹3,999</span>
        </div>
    </div>

    <!-- Live Store Search & Category Filter Navigation -->
    <div style="margin-bottom: 24px; display: flex; flex-direction: column; gap: 14px;">
        <div>
            <input type="text" id="storeSearchInput" class="search-box" oninput="applyFilters()" placeholder="🔍 Instant Search by keyword (e.g. Python, Async, API, CSS, Security, Scraper, Docker...)" autofocus>
        </div>
        <div style="display: flex; gap: 8px; flex-wrap: wrap; align-items: center;">
            <span style="font-size: 12px; color: var(--text-muted); margin-right: 4px;">Filter Tier:</span>
            <button onclick="setCategory('all')" class="cat-btn active" id="btn_all">All Products</button>
            <button onclick="setCategory('cheatsheet')" class="cat-btn" id="btn_cheatsheet">Cheatsheets (₹399)</button>
            <button onclick="setCategory('research')" class="cat-btn" id="btn_research">Research (₹799)</button>
            <button onclick="setCategory('toolkit')" class="cat-btn" id="btn_toolkit">Toolkits (₹1,799)</button>
            <button onclick="setCategory('enterprise')" class="cat-btn" id="btn_enterprise">Enterprise (₹3,999)</button>
        </div>
    </div>

    <div id="storeGrid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 18px;">
        __PRODUCTS_CARDS__
    </div>

    <div id="noMatchMessage" style="display: none; text-align: center; padding: 40px; color: var(--text-muted); background: rgba(18, 24, 38, 0.5); border-radius: 12px; border: 1px dashed rgba(255,255,255,0.1); margin-top: 20px;">
        <i class="fa-solid fa-magnifying-glass" style="font-size: 28px; margin-bottom: 10px; color: #64748b;"></i>
        <h3 style="color: #cbd5e1; margin: 4px 0;">No matching toolkits found</h3>
        <p style="font-size: 13px;">Try searching for another keyword like "Python", "API", or select "All".</p>
    </div>

    <script>
        var selectedCat = 'all';
        function setCategory(cat) {
            selectedCat = cat;
            document.querySelectorAll('.cat-btn').forEach(function(b) { b.classList.remove('active'); });
            var b = document.getElementById('btn_' + cat);
            if (b) b.classList.add('active');
            applyFilters();
        }
        function applyFilters() {
            var q = (document.getElementById('storeSearchInput').value || '').toLowerCase().trim();
            var cards = document.querySelectorAll('.product-card');
            var visible = 0;
            cards.forEach(function(card) {
                var searchBlob = (card.getAttribute('data-search') || '').toLowerCase();
                var catBlob = (card.getAttribute('data-category') || '').toLowerCase();
                var qMatch = !q || searchBlob.indexOf(q) !== -1;
                var catMatch = selectedCat === 'all' || catBlob.indexOf(selectedCat) !== -1;
                if (qMatch && catMatch) {
                    card.style.display = 'flex';
                    visible++;
                } else {
                    card.style.display = 'none';
                }
            });
            var msg = document.getElementById('noMatchMessage');
            if (msg) msg.style.display = (visible === 0) ? 'block' : 'none';
        }
        function openTrackModal() {
            var m = document.getElementById('trackModal');
            if (m) m.style.display = 'flex';
        }
        function closeTrackModal() {
            var m = document.getElementById('trackModal');
            if (m) m.style.display = 'none';
        }
        async function lookupOrder() {
            var q = (document.getElementById('trackInput').value || '').trim();
            var btn = document.getElementById('trackBtn');
            var resBox = document.getElementById('trackResult');
            if (!q) { alert('Please enter your 12-digit UPI UTR number or product keyword.'); return; }
            btn.disabled = true;
            btn.innerText = 'Searching...';
            resBox.style.display = 'block';
            resBox.style.background = 'rgba(255,255,255,0.05)';
            resBox.innerHTML = '<span style="color: #94a3b8;"><i class="fa-solid fa-spinner fa-spin"></i> Checking enterprise ledger...</span>';
            try {
                var res = await fetch('/api/customer/track', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ query: q })
                });
                var d = await res.json();
                if (res.ok && d.found) {
                    resBox.style.background = 'rgba(16, 185, 129, 0.15)';
                    resBox.style.border = '1px solid #10b981';
                    resBox.innerHTML = '<div style="color: #34d399; font-weight: 700; margin-bottom: 6px;"><i class="fa-solid fa-circle-check"></i> ' + d.message + '</div>' +
                        '<div style="display: flex; gap: 8px; margin-top: 10px;">' +
                            '<a href="' + d.download_url + '" class="btn-action purple" style="text-decoration: none; padding: 8px 14px; font-size: 12px; font-weight: 700;"><i class="fa-solid fa-download"></i> Download Package (ZIP)</a>' +
                            '<a href="' + d.preview_url + '" target="_blank" class="btn-action" style="text-decoration: none; padding: 8px 14px; font-size: 12px;"><i class="fa-solid fa-eye"></i> View Preview</a>' +
                        '</div>';
                } else {
                    resBox.style.background = 'rgba(239, 68, 68, 0.15)';
                    resBox.style.border = '1px solid #ef4444';
                    resBox.innerHTML = '<span style="color: #f87171;">' + (d.message || 'No matching delivery found.') + '</span>';
                }
            } catch (e) {
                resBox.style.background = 'rgba(239, 68, 68, 0.15)';
                resBox.innerHTML = '<span style="color: #f87171;">Search error: ' + e + '</span>';
            } finally {
                btn.disabled = false;
                btn.innerText = 'Find';
            }
        }
    </script>

    <!-- Order Tracking & UTR Delivery Retrieval Modal -->
    <div id="trackModal" style="display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.75); backdrop-filter: blur(8px); z-index: 9999; align-items: center; justify-content: center; padding: 20px;">
        <div style="background: rgba(18, 24, 38, 0.98); border: 1px solid var(--card-border); border-radius: 14px; max-width: 520px; width: 100%; padding: 28px; box-shadow: 0 20px 40px rgba(0,0,0,0.5);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px;">
                <h3 style="color: #f8fafc; margin: 0; font-size: 18px;"><i class="fa-solid fa-magnifying-glass"></i> Track Order / Retrieve by UTR</h3>
                <button onclick="closeTrackModal()" style="background: transparent; border: none; color: #94a3b8; font-size: 24px; cursor: pointer;">&times;</button>
            </div>
            <p style="color: var(--text-muted); font-size: 13px; margin: 0 0 16px 0;">Enter your 12-digit bank UPI UTR number or the product name to locate and download your purchased deliverable.</p>
            <div style="display: flex; gap: 8px;">
                <input type="text" id="trackInput" placeholder="Enter 12-digit UTR or product keyword..." style="flex: 1; background: rgba(0,0,0,0.3); border: 1px solid var(--card-border); color: #fff; padding: 10px 14px; border-radius: 8px; font-size: 13px;">
                <button onclick="lookupOrder()" id="trackBtn" class="btn-action purple" style="padding: 10px 16px; font-weight: 700;">Find</button>
            </div>
            <div id="trackResult" style="margin-top: 14px; display: none; padding: 14px; border-radius: 8px; font-size: 13px;"></div>
        </div>
    </div>

    <footer style="margin-top: 50px; padding: 24px 0; border-top: 1px solid rgba(255,255,255,0.08); text-align: center; font-size: 13px; color: #64748b;">
        <div style="display: flex; justify-content: center; gap: 20px; flex-wrap: wrap; margin-bottom: 8px;">
            <a href="/terms" target="_blank" style="color: #94a3b8; text-decoration: none;"><i class="fa-solid fa-scale-balanced"></i> Master Terms of Service & AI Disclaimers</a>
            <a href="/hire" style="color: #94a3b8; text-decoration: none;"><i class="fa-solid fa-briefcase"></i> Commission Custom Work</a>
            <a href="https://wa.me/919999999999?text=Hi%20Alpesh,%20I%20have%20an%20inquiry" target="_blank" style="color: #4ade80; text-decoration: none;"><i class="fa-brands fa-whatsapp"></i> WhatsApp Reach</a>
        </div>
        <p style="margin: 0; font-size: 12px; color: #475569;">
            MicroCorp AI is an autonomous AI software engineering fleet operated by Alpesh Thakor (UPI: <strong>talpesh100@ybl</strong>). All deliverables are provided strictly on an <strong>AS-IS</strong> basis with all faults and without warranty. Exclusive jurisdiction: Ahmedabad, Gujarat, India.
        </p>
    </footer>
</body>
</html>"""

HIRE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hire MicroCorp AI — Autonomous Software Engineering Fleet</title>
    <meta name="description" content="Commission custom turnkey software engineering from MicroCorp AI: full-stack backends, microservices, and automation pipelines. Direct UPI settlement to talpesh100@ybl.">
    <link rel="stylesheet" href="/static/css/style.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <style>
        body { max-width: 880px; margin: 30px auto; padding: 20px; }
        .hero { background: linear-gradient(135deg, rgba(30, 41, 59, 0.95), rgba(15, 23, 42, 0.98)); border: 1px solid var(--card-border); padding: 36px; border-radius: 16px; margin-bottom: 24px; }
        .form-box { background: rgba(18, 24, 38, 0.95); border: 1px solid var(--card-border); border-radius: 14px; padding: 32px; margin-bottom: 24px; }
        .form-group { margin-bottom: 18px; }
        .form-group label { display: block; font-size: 13px; font-weight: 600; color: #cbd5e1; margin-bottom: 6px; }
        .form-control { width: 100%; box-sizing: border-box; background: rgba(0,0,0,0.3); border: 1px solid var(--card-border); color: #f8fafc; padding: 12px 14px; border-radius: 8px; font-size: 14px; outline: none; }
        .form-control:focus { border-color: #3b82f6; }
        textarea.form-control { min-height: 110px; resize: vertical; line-height: 1.5; }
        .pills { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 14px; }
        .pill { background: rgba(59, 130, 246, 0.15); border: 1px solid rgba(59, 130, 246, 0.3); color: #60a5fa; font-size: 12px; font-weight: 600; padding: 4px 10px; border-radius: 6px; }
    </style>
</head>
<body>
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; flex-wrap: wrap; gap: 10px;">
        <div style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap;">
            <a href="/store" class="btn-action" style="display: inline-flex; text-decoration: none;"><i class="fa-solid fa-arrow-left"></i> Digital Store</a>
            <a href="/" class="btn-action" style="display: inline-flex; text-decoration: none;"><i class="fa-solid fa-gauge"></i> Console</a>
            <a href="https://wa.me/919999999999?text=Hi%20Alpesh,%20I%20want%20to%20discuss%20a%20custom%20software%20project" target="_blank" class="btn-action" style="display: inline-flex; align-items: center; gap: 6px; text-decoration: none; background: rgba(37, 211, 102, 0.15); border: 1px solid rgba(37, 211, 102, 0.3); color: #4ade80;">
                <i class="fa-brands fa-whatsapp"></i> Chat on WhatsApp
            </a>
        </div>
        <div class="payout-tag" style="background: rgba(16, 185, 129, 0.15); border: 1px solid rgba(16, 185, 129, 0.3); color: #34d399; padding: 6px 14px; border-radius: 999px; font-size: 13px; font-weight: 600;">
            <i class="fa-solid fa-circle-check"></i> Payee UPI: <strong>__PAYOUT_UPI_ID__</strong> (__PAYEE_NAME__)
        </div>
    </div>

    <div class="hero">
        <span class="badge-tag" style="background: rgba(139, 92, 246, 0.2); color: #c084fc; margin-bottom: 12px; display: inline-block;">COMMISSION AUTONOMOUS ENGINEERING</span>
        <h1 style="color: #f8fafc; font-size: 30px; margin: 4px 0 10px 0;">Hire MicroCorp AI for Custom Projects</h1>
        <p style="color: #94a3b8; font-size: 14px; line-height: 1.6; margin: 0;">
            Commission custom software from our 24/7 autonomous engineering fleet. Every project deliverable includes modular production code, unit tests, Docker configs, 1-click launchers (<code>START_HERE.html</code> & <code>RUN_WINDOWS.bat</code>), and full commercial ownership rights transfer.
        </p>
        <div class="pills">
            <span class="pill"><i class="fa-solid fa-shield-halved"></i> 100% Legal & Ethical</span>
            <span class="pill"><i class="fa-solid fa-bolt"></i> 0.5s Automated Feasibility Check</span>
            <span class="pill"><i class="fa-solid fa-file-zipper"></i> Turnkey ZIP Delivery</span>
            <span class="pill"><i class="fa-solid fa-credit-card"></i> Direct UPI Settlement (Zero Fees)</span>
        </div>
    </div>

    <div class="form-box">
        <h3 style="color: #f1f5f9; font-size: 18px; margin: 0 0 18px 0; border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 12px;">
            <i class="fa-solid fa-file-pen" style="color: #60a5fa;"></i> Project Commission Request
        </h3>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
            <div class="form-group">
                <label>Your Name / Organization</label>
                <input type="text" id="orderClientName" class="form-control" placeholder="e.g. Acme Tech Studio">
            </div>
            <div class="form-group">
                <label>Email or WhatsApp Contact</label>
                <input type="text" id="orderClientContact" class="form-control" placeholder="e.g. client@company.com or +91 98...">
            </div>
        </div>

        <div class="form-group">
            <label>Project Title / Core Requirement</label>
            <input type="text" id="orderProjectTitle" class="form-control" placeholder="e.g. FastAPI Async Webhook Microservice with Docker & Docs">
        </div>

        <div class="form-group">
            <label>Detailed Technical Scope & Deliverables</label>
            <textarea id="orderProjectReqs" class="form-control" placeholder="Describe the required features, APIs, database requirements, or architecture patterns..."></textarea>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
            <div class="form-group">
                <label>Target Budget (USD / INR)</label>
                <input type="number" id="orderBudget" class="form-control" placeholder="e.g. 150 ($ USD)" value="150">
            </div>
            <div class="form-group" style="display: flex; align-items: flex-end;">
                <button onclick="submitHireOrder()" id="orderSubmitBtn" class="btn-action purple" style="width: 100%; padding: 12px; font-weight: 700; font-size: 14px;">
                    <i class="fa-solid fa-paper-plane"></i> Submit & Audit Project
                </button>
            </div>
        </div>

        <div class="form-group" style="background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.08); padding: 12px 14px; border-radius: 8px; font-size: 12px; color: #94a3b8; line-height: 1.5; margin-top: 14px;">
            <label style="display: flex; align-items: flex-start; gap: 8px; cursor: pointer;">
                <input type="checkbox" id="termsCheckHire" checked style="margin-top: 3px;">
                <span>I confirm I am 18+, acknowledge all software is engineered autonomously by AI on a strict <strong>AS-IS</strong> basis with 100% client assumption of risk, and unconditionally agree to the <a href="/terms" target="_blank" style="color: #60a5fa; text-decoration: underline;">Master Terms of Service, Limitation of Liability & AI Disclaimers</a> (Jurisdiction: Ahmedabad, India).</span>
            </label>
        </div>

        <div id="hireResultBox" style="display: none; margin-top: 20px; padding: 20px; border-radius: 10px;"></div>
    </div>

    <script>
        async function submitHireOrder() {
            var name = document.getElementById('orderClientName').value.trim() || 'Client';
            var contact = document.getElementById('orderClientContact').value.trim();
            var title = document.getElementById('orderProjectTitle').value.trim();
            var reqs = document.getElementById('orderProjectReqs').value.trim();
            var budget = parseFloat(document.getElementById('orderBudget').value) || 50.0;
            var btn = document.getElementById('orderSubmitBtn');
            var resBox = document.getElementById('hireResultBox');

            var termsCheck = document.getElementById('termsCheckHire');
            if (termsCheck && !termsCheck.checked) {
                alert('You must accept the Master Terms of Service and AI Liability Disclaimer to submit a project.');
                return;
            }

            if (!title || !reqs) {
                alert('Please enter a project title and technical requirements.');
                return;
            }

            btn.disabled = true;
            btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Auditing with Legal Guardian...';
            resBox.style.display = 'block';
            resBox.style.background = 'rgba(255,255,255,0.05)';
            resBox.style.border = '1px solid rgba(255,255,255,0.1)';
            resBox.innerHTML = '<div style="color: #60a5fa;"><i class="fa-solid fa-spinner fa-spin"></i> Running automated legal audit and technical feasibility evaluation...</div>';

            try {
                var res = await fetch('/api/customer/order', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        customer_name: name,
                        customer_email: contact,
                        project_title: title,
                        project_requirements: reqs,
                        budget_usd: budget
                    })
                });
                var d = await res.json();
                if (res.ok && d.status === 'ACCEPTED_LAWFUL') {
                    resBox.style.background = 'rgba(16, 185, 129, 0.15)';
                    resBox.style.border = '1px solid #10b981';
                    resBox.innerHTML = '<div style="color: #34d399; font-weight: 800; font-size: 16px;"><i class="fa-solid fa-circle-check"></i> Project Accepted & Verified Lawful!</div>' +
                        '<p style="color: #cbd5e1; font-size: 13px; margin: 8px 0 14px 0;">' + d.message + '</p>' +
                        '<div style="background: rgba(0,0,0,0.3); padding: 14px; border-radius: 8px; margin-bottom: 14px; font-size: 13px; color: #cbd5e1;">' +
                            '<div><strong>Task ID:</strong> <code>' + d.task_id + '</code></div>' +
                            '<div><strong>Agreed Budget:</strong> $' + (d.amount_usd || budget) + ' USD (~₹' + (d.amount_inr || Math.round(budget * 86.5)) + ' INR)</div>' +
                            '<div><strong>Official Beneficiary UPI ID:</strong> <code>' + (d.payout_upi_id || 'talpesh100@ybl') + '</code> (' + (d.payee_name || 'Alpesh Thakor') + ')</div>' +
                        '</div>' +
                        '<div style="display: flex; gap: 10px; flex-wrap: wrap;">' +
                            '<a href="' + (d.upi_uri || 'upi://pay?pa=talpesh100@ybl') + '" class="btn-action purple" style="text-decoration: none; padding: 10px 18px; font-weight: 700;">' +
                            '<i class="fa-solid fa-bolt"></i> Lock-In Order via UPI App</a>' +
                            '<a href="https://wa.me/919999999999?text=Hi%20Alpesh,%20I%20just%20submitted%20project%20order%20' + d.task_id + ':%20' + encodeURIComponent(title) + '" target="_blank" class="btn-action" style="text-decoration: none; padding: 10px 18px; background: rgba(37, 211, 102, 0.15); border: 1px solid rgba(37, 211, 102, 0.3); color: #4ade80;">' +
                            '<i class="fa-brands fa-whatsapp"></i> Confirm on WhatsApp</a>' +
                        '</div>';
                } else {
                    resBox.style.background = 'rgba(239, 68, 68, 0.15)';
                    resBox.style.border = '1px solid #ef4444';
                    resBox.innerHTML = '<div style="color: #f87171; font-weight: 800; font-size: 15px;"><i class="fa-solid fa-triangle-exclamation"></i> Project Blocked on Legal/Ethical Grounds</div>' +
                        '<p style="color: #cbd5e1; font-size: 13px; margin: 6px 0;"><strong>Category:</strong> ' + (d.risk_category || 'LEGAL_VIOLATION') + '</p>' +
                        '<p style="color: #94a3b8; font-size: 12px; margin: 0;">' + (d.reason || d.detail || 'MicroCorp AI strictly operates within legal and ethical boundaries.') + '</p>';
                }
            } catch (e) {
                resBox.style.background = 'rgba(239, 68, 68, 0.15)';
                resBox.innerHTML = '<span style="color: #f87171;">Submission error: ' + e + '</span>';
            } finally {
                btn.disabled = false;
                btn.innerHTML = '<i class="fa-solid fa-paper-plane"></i> Submit & Audit Project';
            }
        }
    </script>
</body>
</html>"""

CHECKOUT_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Instant UPI Checkout - __TITLE__</title>
    <link rel="stylesheet" href="/static/css/style.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <style>
        body { max-width: 780px; margin: 40px auto; padding: 20px; }
        .checkout-box { background: rgba(18, 24, 38, 0.95); border: 1px solid var(--card-border); border-radius: 14px; padding: 36px; }
        .qr-card { background: #ffffff; padding: 12px; border-radius: 12px; border: 2px solid #86efac; display: inline-flex; align-items: center; justify-content: center; width: 220px; height: 220px; overflow: hidden; }
    </style>
</head>
<body>
    <div style="margin-bottom: 20px;">
        <a href="/store" class="btn-action" style="display: inline-flex; text-decoration: none;"><i class="fa-solid fa-arrow-left"></i> Back to Store</a>
    </div>

    <div class="checkout-box">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 10px; border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 20px;">
            <div>
                <span class="badge-tag" style="background: rgba(16, 185, 129, 0.2); color: #34d399;"><i class="fa-solid fa-bolt"></i> Instant UPI Settlement</span>
                <h2 style="color: #f8fafc; font-size: 24px; margin-top: 8px;">__TITLE__</h2>
                <small style="color: var(--text-muted);">Commercial License • Instant ZIP Delivery</small>
            </div>
            <div style="text-align: right;">
                <span style="font-size: 28px; font-weight: 800; color: #34d399;">₹__AMOUNT_INR__</span>
                <span style="display: block; font-size: 13px; color: #94a3b8;">(~__PRICE_USD__ USD)</span>
            </div>
        </div>

        <div style="display: flex; gap: 30px; margin-top: 26px; flex-wrap: wrap; align-items: center;">
            <div class="qr-card">
                __QR_SVG__
            </div>
            <div style="flex: 1; min-width: 260px;">
                <h4 style="color: #f1f5f9; font-size: 16px; margin: 0 0 10px 0;">Scan to Pay with Any UPI App</h4>
                <div style="background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08); padding: 12px; border-radius: 8px; margin-bottom: 14px;">
                    <div style="font-size: 12px; color: var(--text-muted);">Official Payee UPI ID:</div>
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 4px;">
                        <strong style="color: #34d399; font-size: 15px; font-family: monospace;">__UPI_ID__</strong>
                        <button class="btn-action" onclick="navigator.clipboard.writeText('__UPI_ID__'); alert('Copied UPI ID: __UPI_ID__')" style="padding: 4px 10px; font-size: 11px;">Copy</button>
                    </div>
                    <div style="font-size: 12px; color: #cbd5e1; margin-top: 4px;">Name: <strong>__PAYEE_NAME__</strong></div>
                </div>

                <a href="__UPI_URI__" class="btn-action purple" style="display: block; text-align: center; padding: 12px; text-decoration: none; font-size: 14px; font-weight: 700;">
                    <i class="fa-solid fa-mobile-screen"></i> Pay on Mobile App (PhonePe / GPay)
                </a>
            </div>
        </div>

        <div style="margin-top: 30px; padding-top: 24px; border-top: 1px solid rgba(255,255,255,0.08);">
            <h4 style="color: #f1f5f9; font-size: 15px;"><i class="fa-solid fa-key"></i> Step 2: Confirm Payment & Unlock Download</h4>
            <p style="color: var(--text-muted); font-size: 13px; margin: 4px 0 16px 0;">After sending ₹__AMOUNT_INR__ to <code>__UPI_ID__</code>, enter your 12-digit UPI UTR / Transaction Reference Number below to immediately unlock your product.</p>

            <div style="margin-bottom: 14px; padding: 12px; background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; font-size: 12px; color: #94a3b8; line-height: 1.5;">
                <label style="display: flex; align-items: flex-start; gap: 8px; cursor: pointer;">
                    <input type="checkbox" id="termsCheckCheckout" checked style="margin-top: 2px;">
                    <span>I confirm I am 18+, acknowledge all deliverables are generated autonomously by AI on a strict <strong>AS-IS</strong> basis, assume 100% deployment and auditing responsibility, and agree to the <a href="/terms" target="_blank" style="color: #60a5fa; text-decoration: underline;">Master Terms of Service & AI Disclaimers</a> (Jurisdiction: Ahmedabad, India).</span>
                </label>
            </div>

            <div style="display: grid; grid-template-columns: 2fr 1fr; gap: 10px;">
                <input type="text" id="utrNumber" placeholder="Enter 12-digit UPI UTR / Transaction ID (e.g. 429182749102)" style="background: rgba(0,0,0,0.3); border: 1px solid var(--card-border); color: #fff; padding: 12px; border-radius: 8px; font-size: 14px;">
                <button class="btn-action" onclick="verifyUTR()" id="verifyBtn" style="background: #10b981; color: #fff; border: none; font-weight: 700; padding: 12px;">
                    Verify & Download
                </button>
            </div>
            <div id="utrResult" style="margin-top: 14px; display: none; padding: 14px; border-radius: 8px;"></div>
        </div>
    </div>

    <script>
        async function verifyUTR() {
            var termsCheck = document.getElementById("termsCheckCheckout");
            if (termsCheck && !termsCheck.checked) {
                alert("You must agree to the Master Terms of Service and AI Liability Disclaimer to download.");
                return;
            }
            var utr = document.getElementById("utrNumber").value.trim();
            var btn = document.getElementById("verifyBtn");
            var resDiv = document.getElementById("utrResult");
            if (!utr) { alert("Please enter the UTR or Transaction ID from your payment app."); return; }
            
            btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Verifying...';
            btn.disabled = true;

            try {
                var res = await fetch("/api/payment/verify", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        order_id: "__ORDER_ID__",
                        utr_number: utr,
                        amount_inr: __AMOUNT_INR__,
                        asset_id: "__ASSET_ID__"
                    })
                });
                var d = await res.json();
                resDiv.style.display = "block";
                if (res.ok && d.success) {
                    resDiv.style.background = "rgba(16, 185, 129, 0.2)";
                    resDiv.style.border = "1px solid #10b981";
                    resDiv.innerHTML = '<div style="color: #34d399; font-weight: 700; font-size: 15px;"><i class="fa-solid fa-circle-check"></i> Payment Verified!</div>' +
                        '<p style="color: #cbd5e1; font-size: 13px; margin: 6px 0 12px 0;">' + d.message + '</p>' +
                        '<a href="' + d.download_url + '" class="btn-action" style="background: #10b981; color: #fff; text-decoration: none; display: inline-block; padding: 12px 22px; font-weight: 700; font-size: 14px;">' +
                        '<i class="fa-solid fa-download"></i> Download Purchased Asset (ZIP)</a>' +
                        '<div style="margin-top: 18px; padding: 16px; background: rgba(0,0,0,0.3); border: 1px solid rgba(16,185,129,0.3); border-radius: 8px; text-align: left;">' +
                            '<div style="color: #34d399; font-weight: 700; font-size: 13px; margin-bottom: 6px;"><i class="fa-solid fa-rocket"></i> How to Use Your Download in 60 Seconds:</div>' +
                            '<ol style="margin: 0; padding-left: 20px; font-size: 13px; color: #cbd5e1; line-height: 1.7;">' +
                                '<li><strong>Unzip</strong> the downloaded file to any folder on your computer.</li>' +
                                '<li><strong>Double-click <code>START_HERE.html</code></strong> to open your interactive dashboard, read documentation, and copy code snippets with 1 click.</li>' +
                                '<li><strong>1-Click Launch:</strong> On Windows double-click <code>RUN_WINDOWS.bat</code>, or on Mac/Linux run <code>bash RUN_MAC_LINUX.sh</code>.</li>' +
                            '</ol>' +
                        '</div>';
                } else {
                    resDiv.style.background = "rgba(239, 68, 68, 0.2)";
                    resDiv.style.border = "1px solid #ef4444";
                    resDiv.innerHTML = '<span style="color: #f87171;"><i class="fa-solid fa-triangle-exclamation"></i> ' + (d.detail || d.error || 'Verification failed. Please check the UTR number.') + '</span>';
                }
            } catch (e) {
                resDiv.style.display = "block";
                resDiv.style.background = "rgba(239, 68, 68, 0.2)";
                resDiv.innerHTML = '<span style="color: #f87171;">Error: ' + e + '</span>';
            } finally {
                btn.innerHTML = 'Verify & Download';
                btn.disabled = false;
            }
        }
    </script>
</body>
</html>"""

@app.get("/store", response_class=HTMLResponse)
async def public_storefront():
    from core.upi_payment import upi_gateway
    from core.pricing_engine import pricing_engine
    ready_dir = DELIVERABLES_DIR / "ready_to_monetize"
    products = []
    if ready_dir.exists():
        for zip_p in sorted(ready_dir.glob("*.zip"), reverse=True):
            clean_name = zip_p.stem
            size_kb = round(zip_p.stat().st_size / 1024, 1)
            title_guess = re.sub(r'^\d+_\d+_', '', clean_name).replace("_", " ").title()
            pricing = pricing_engine.get_pricing_for_asset(title=title_guess)
            products.append({
                "slug": clean_name,
                "title": title_guess,
                "size_kb": size_kb,
                "price_usd": pricing["price_usd"],
                "price_inr": pricing["price_inr"],
                "badge": pricing["badge"],
                "badge_style": pricing["badge_style"],
                "tier_name": pricing["tier_name"],
                "description": pricing["description"],
                "download_name": zip_p.name
            })
            
    products_cards_html = ""
    for p in products[:60]:
        cat_tag = "cheatsheet" if "cheatsheet" in p['tier_name'].lower() else ("research" if "research" in p['tier_name'].lower() else ("enterprise" if "enterprise" in p['tier_name'].lower() else "toolkit"))
        search_blob = f"{p['title']} {p['description']} {p['slug']} {p['tier_name']}".lower().replace('"', '&quot;')
        products_cards_html += f"""
        <div class="product-card" data-category="{cat_tag}" data-search="{search_blob}" style="background: rgba(18, 24, 38, 0.95); border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; padding: 22px; display: flex; flex-direction: column; justify-content: space-between;">
            <div>
                <span style="{p['badge_style']} font-size: 11px; font-weight: 700; padding: 3px 8px; border-radius: 999px;">{p['badge']}</span>
                <h3 style="color: #f1f5f9; font-size: 17px; margin: 10px 0 6px 0; line-height: 1.4;">{p['title']}</h3>
                <p style="color: #94a3b8; font-size: 13px; line-height: 1.5;">{p['description']}</p>
                <div style="color: #64748b; font-size: 12px; margin-top: 8px;"><i class="fa-solid fa-file-zipper"></i> Packaged ZIP ({p['size_kb']} KB)</div>
            </div>
            <div style="margin-top: 20px; padding-top: 14px; border-top: 1px solid rgba(255,255,255,0.08); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
                <div>
                    <span style="font-size: 20px; font-weight: 800; color: #34d399;">₹{p['price_inr']}</span>
                    <small style="color: #94a3b8; font-size: 12px; display: block;">(~${p['price_usd']:.2f} USD)</small>
                </div>
                <div style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap;">
                    <a href="/view_deliverable/ready_to_monetize/{p['slug']}.html" target="_blank" style="background: rgba(96, 165, 250, 0.12); border: 1px solid rgba(96, 165, 250, 0.3); color: #93c5fd; text-decoration: none; padding: 8px 12px; border-radius: 8px; font-size: 12px; font-weight: 600; display: inline-flex; align-items: center; gap: 5px;" title="Preview full technical guide & blueprints">
                        <i class="fa-solid fa-eye"></i> Preview
                    </a>
                    <a href="/api/ecommerce/syndicate/{p['slug']}" target="_blank" style="background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.12); color: #cbd5e1; text-decoration: none; padding: 8px 12px; border-radius: 8px; font-size: 12px; font-weight: 600; display: inline-flex; align-items: center; gap: 5px;" title="View Amazon, Flipkart, Meesho, and Gumroad Seller Pack">
                        <i class="fa-solid fa-cart-shopping"></i> Marketplace Pack
                    </a>
                    <a href="/checkout/{p['slug']}" style="background: linear-gradient(135deg, #10b981, #059669); color: #ffffff; text-decoration: none; padding: 8px 16px; border-radius: 8px; font-size: 13px; font-weight: 700; display: inline-flex; align-items: center; gap: 6px;">
                        <i class="fa-solid fa-bolt"></i> Buy with UPI
                    </a>
                </div>
            </div>
        </div>
        """

    empty_msg = '<div style="color: var(--text-muted); padding: 30px; grid-column: 1 / -1; text-align: center;">No commercial products ready yet. The agent is continuously manufacturing assets in the background.</div>'
    html = STORE_TEMPLATE.replace("__PAYOUT_UPI_ID__", upi_gateway.upi_id) \
                          .replace("__PAYEE_NAME__", upi_gateway.payee_name) \
                          .replace("__TOTAL_COUNT__", str(len(products))) \
                          .replace("__PRODUCTS_CARDS__", products_cards_html or empty_msg)
    return HTMLResponse(content=html)

@app.get("/hire", response_class=HTMLResponse)
@app.get("/order", response_class=HTMLResponse)
async def hire_page():
    from core.upi_payment import upi_gateway
    html = HIRE_TEMPLATE.replace("__PAYOUT_UPI_ID__", upi_gateway.upi_id) \
                          .replace("__PAYEE_NAME__", upi_gateway.payee_name)
    return HTMLResponse(content=html)

@app.get("/sitemap.xml")
async def sitemap_endpoint():
    from core.tunnel_gateway import public_gateway
    base_url = public_gateway.get_public_url() or "http://127.0.0.1:8585"
    ready_dir = DELIVERABLES_DIR / "ready_to_monetize"
    urls = [
        f"<url><loc>{base_url}/</loc><changefreq>hourly</changefreq><priority>1.0</priority></url>",
        f"<url><loc>{base_url}/store</loc><changefreq>hourly</changefreq><priority>0.9</priority></url>",
        f"<url><loc>{base_url}/hire</loc><changefreq>daily</changefreq><priority>0.9</priority></url>",
        f"<url><loc>{base_url}/terms</loc><changefreq>weekly</changefreq><priority>0.5</priority></url>"
    ]
    if ready_dir.exists():
        for p in sorted(ready_dir.glob("*.html")):
            clean_name = p.stem
            urls.append(f"<url><loc>{base_url}/view_deliverable/ready_to_monetize/{clean_name}.html</loc><changefreq>daily</changefreq><priority>0.8</priority></url>")
            urls.append(f"<url><loc>{base_url}/checkout/{clean_name}</loc><changefreq>daily</changefreq><priority>0.7</priority></url>")
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{"".join(urls)}
</urlset>"""
    return Response(content=xml, media_type="application/xml")

@app.get("/robots.txt")
async def robots_endpoint():
    from core.tunnel_gateway import public_gateway
    base_url = public_gateway.get_public_url() or "http://127.0.0.1:8585"
    txt = f"""User-agent: *
Allow: /
Allow: /store
Allow: /hire
Allow: /order
Allow: /checkout/
Allow: /view_deliverable/
Sitemap: {base_url}/sitemap.xml
"""
    return Response(content=txt, media_type="text/plain")

@app.get("/api/freelance/recent_deliveries")
async def get_recent_freelance_deliveries():
    fl_dir = DELIVERABLES_DIR / "freelance_turnkey"
    deliveries = []
    if fl_dir.exists():
        for zip_f in sorted(fl_dir.glob("*.zip"), key=os.path.getmtime, reverse=True)[:10]:
            stem = zip_f.stem
            html_f = zip_f.with_suffix(".html")
            msg_f = zip_f.parent / f"{stem}_CLIENT_MESSAGE.txt"
            msg_text = msg_f.read_text(encoding="utf-8") if msg_f.exists() else ""
            parts = stem.split("_", 2)
            platform = "Fiverr"
            if len(parts) > 2:
                for p_name in ["fiverr", "upwork", "freelancer", "remoteok"]:
                    if p_name in stem.lower():
                        platform = p_name.title()
                        break
            deliveries.append({
                "slug": stem,
                "title": stem.replace("_", " ").title(),
                "platform": platform,
                "zip_path": f"/view_deliverable/freelance_turnkey/{zip_f.name}?download=true",
                "html_path": f"/view_deliverable/freelance_turnkey/{html_f.name}" if html_f.exists() else f"/view_deliverable/freelance_turnkey/{zip_f.name}",
                "client_message": msg_text,
                "size_kb": round(zip_f.stat().st_size / 1024, 1),
                "created_at": datetime.fromtimestamp(zip_f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            })
    return deliveries

@app.get("/api/promotions/latest")
async def get_latest_promotions():
    promo_dir = DELIVERABLES_DIR / "promotions"
    promos = []
    if promo_dir.exists():
        for p in sorted(promo_dir.glob("*.md"), key=os.path.getmtime, reverse=True)[:5]:
            try:
                promos.append({
                    "filename": p.name,
                    "title": p.stem.replace("_", " ").title(),
                    "content": p.read_text(encoding="utf-8")
                })
            except Exception:
                pass
    return promos

@app.get("/checkout/{asset_id}", response_class=HTMLResponse)
async def checkout_page(asset_id: str):
    from core.upi_payment import upi_gateway
    from core.pricing_engine import pricing_engine
    title = re.sub(r'^\d+_\d+_', '', asset_id).replace("_", " ").title()
    category = "digital_product"
    pricing = pricing_engine.get_pricing_for_asset(title=title, category=category)
    pkg = upi_gateway.create_checkout_package(
        asset_id=asset_id,
        title=title,
        category=category,
        price_usd=pricing["price_usd"],
        custom_price_inr=pricing["price_inr"]
    )

    html = CHECKOUT_TEMPLATE.replace("__TITLE__", title) \
                            .replace("__AMOUNT_INR__", str(pkg['amount_inr'])) \
                            .replace("__PRICE_USD__", f"${pkg['price_usd']:.2f}") \
                            .replace("__QR_SVG__", pkg['qr_svg']) \
                            .replace("__UPI_ID__", pkg['upi_id']) \
                            .replace("__PAYEE_NAME__", pkg['payee_name']) \
                            .replace("__UPI_URI__", pkg['upi_uri']) \
                            .replace("__ORDER_ID__", pkg['order_id']) \
                            .replace("__ASSET_ID__", asset_id)

    return HTMLResponse(content=html)

@app.get("/api/pricing/catalog")
async def get_pricing_catalog():
    from core.pricing_engine import pricing_engine
    return pricing_engine.get_catalog()

@app.get("/api/ecommerce/channels")
async def get_ecommerce_channels():
    from core.ecommerce_syndicator import ecommerce_syndicator
    return {
        "payout_upi_id": ecommerce_syndicator.payout_upi_id,
        "payee_name": ecommerce_syndicator.payee_name,
        "channels": [
            {
                "id": "amazon_kdp",
                "name": "Amazon Kindle Direct Publishing",
                "badge": "Amazon KDP",
                "type": "Digital eBook & Print-on-Demand Paperback",
                "royalty": "70% Digital Royalty",
                "fulfillment": "100% Automated by Amazon (zero inventory)",
                "gst_required": False,
                "supported_marketplaces": ["Amazon.in", "Amazon.com", "Amazon.co.uk"]
            },
            {
                "id": "flipkart_meesho",
                "name": "Flipkart & Meesho Commerce",
                "badge": "Flipkart / Meesho",
                "type": "Physical Spiral Handbook & USB Code Kit",
                "hsn_code": "4901.10.10 (Printed Technical Books)",
                "gst_rate": "0% (GST Exempt in India)",
                "fulfillment": "Courier Pickup via Shadowfax / Delhivery / Ekart",
                "gst_required": True
            },
            {
                "id": "gumroad",
                "name": "Gumroad Global Creator Store",
                "badge": "Gumroad",
                "type": "Direct Global Digital Download",
                "payout": "Direct Bank Deposit / Stripe / PayPal",
                "gst_required": False
            },
            {
                "id": "instamojo",
                "name": "Instamojo & Cosmofeed India",
                "badge": "Instamojo UPI",
                "type": "Instant Indian UPI Digital File Delivery",
                "payout": f"Direct Instant UPI to {ecommerce_syndicator.payout_upi_id}",
                "gst_required": False
            }
        ]
    }

@app.get("/api/ecommerce/syndicate/{asset_id}")
async def get_ecommerce_syndication(asset_id: str):
    from core.ecommerce_syndicator import ecommerce_syndicator
    title = re.sub(r'^\d+_\d+_', '', asset_id).replace("_", " ").title()
    category = "digital_product"
    
    # Try reading existing README or markdown if available
    md_content = f"# {title}\nProduction developer toolkit engineered by MicroCorp AI."
    matches = list(DELIVERABLES_DIR.glob(f"**/*{asset_id}*.md"))
    if matches:
        try:
            md_content = matches[0].read_text(encoding="utf-8")
        except Exception:
            pass

    bundle = ecommerce_syndicator.generate_all_marketplace_packages(
        asset_id=asset_id,
        title=title,
        category=category,
        markdown_content=md_content
    )
    return bundle

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
