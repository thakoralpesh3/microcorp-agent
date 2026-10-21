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
    <title>MicroCorp AI - Official Digital Storefront</title>
    <link rel="stylesheet" href="/static/css/style.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <style>
        body { max-width: 1100px; margin: 30px auto; padding: 20px; }
        .hero { background: linear-gradient(135deg, rgba(30, 41, 59, 0.9), rgba(15, 23, 42, 0.95)); border: 1px solid var(--card-border); padding: 36px; border-radius: 16px; margin-bottom: 28px; }
        .payout-tag { background: rgba(16, 185, 129, 0.15); border: 1px solid rgba(16, 185, 129, 0.3); color: #34d399; padding: 6px 14px; border-radius: 999px; font-size: 13px; font-weight: 600; display: inline-flex; align-items: center; gap: 8px; }
    </style>
</head>
<body>
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
        <a href="/" class="btn-action" style="display: inline-flex; text-decoration: none;"><i class="fa-solid fa-arrow-left"></i> Console Dashboard</a>
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
    </div>

    <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 18px;">
        __PRODUCTS_CARDS__
    </div>
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
                        '<a href="' + d.download_url + '" class="btn-action" style="background: #10b981; color: #fff; text-decoration: none; display: inline-block; padding: 10px 18px; font-weight: 700;">' +
                        '<i class="fa-solid fa-download"></i> Download Purchased Asset (ZIP)</a>';
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
    ready_dir = DELIVERABLES_DIR / "ready_to_monetize"
    products = []
    from core.growth_engine import growth_engine
    dyn_usd, dyn_inr = growth_engine.compute_dynamic_product_price(complexity_score=1.0)
    if ready_dir.exists():
        for zip_p in sorted(ready_dir.glob("*.zip"), reverse=True):
            clean_name = zip_p.stem
            size_kb = round(zip_p.stat().st_size / 1024, 1)
            title_guess = re.sub(r'^\d+_\d+_', '', clean_name).replace("_", " ").title()
            products.append({
                "slug": clean_name,
                "title": title_guess,
                "size_kb": size_kb,
                "price_usd": dyn_usd,
                "price_inr": dyn_inr,
                "download_name": zip_p.name
            })
            
    products_cards_html = ""
    for p in products[:12]:
        products_cards_html += f"""
        <div style="background: rgba(18, 24, 38, 0.95); border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; padding: 22px; display: flex; flex-direction: column; justify-content: space-between;">
            <div>
                <span style="background: rgba(59, 130, 246, 0.2); color: #60a5fa; font-size: 11px; font-weight: 700; padding: 3px 8px; border-radius: 999px;">DIGITAL ASSET</span>
                <h3 style="color: #f1f5f9; font-size: 17px; margin: 10px 0 6px 0; line-height: 1.4;">{p['title']}</h3>
                <p style="color: #94a3b8; font-size: 13px; line-height: 1.5;">Production-grade architecture guide, copy-paste code snippets, documentation, and commercial license.</p>
                <div style="color: #64748b; font-size: 12px; margin-top: 8px;"><i class="fa-solid fa-file-zipper"></i> Packaged ZIP ({p['size_kb']} KB)</div>
            </div>
            <div style="margin-top: 20px; padding-top: 14px; border-top: 1px solid rgba(255,255,255,0.08); display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <span style="font-size: 20px; font-weight: 800; color: #34d399;">₹{p['price_inr']}</span>
                    <small style="color: #94a3b8; font-size: 12px; display: block;">(~${p['price_usd']:.2f} USD)</small>
                </div>
                <a href="/checkout/{p['slug']}" style="background: linear-gradient(135deg, #10b981, #059669); color: #ffffff; text-decoration: none; padding: 8px 16px; border-radius: 8px; font-size: 13px; font-weight: 700; display: inline-flex; align-items: center; gap: 6px;">
                    <i class="fa-solid fa-bolt"></i> Buy with UPI
                </a>
            </div>
        </div>
        """

    empty_msg = '<div style="color: var(--text-muted); padding: 30px; grid-column: 1 / -1; text-align: center;">No commercial products ready yet. The agent is continuously manufacturing assets in the background.</div>'
    html = STORE_TEMPLATE.replace("__PAYOUT_UPI_ID__", upi_gateway.upi_id) \
                          .replace("__PAYEE_NAME__", upi_gateway.payee_name) \
                          .replace("__PRODUCTS_CARDS__", products_cards_html or empty_msg)
    return HTMLResponse(content=html)

@app.get("/checkout/{asset_id}", response_class=HTMLResponse)
async def checkout_page(asset_id: str):
    from core.upi_payment import upi_gateway
    title = asset_id.replace("_", " ").title()
    from core.growth_engine import growth_engine
    dyn_usd, _ = growth_engine.compute_dynamic_product_price(complexity_score=1.0)
    pkg = upi_gateway.create_checkout_package(asset_id=asset_id, title=title, category=category, price_usd=dyn_usd)

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
