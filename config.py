"""
MicroCorp AI - Configuration Module
Manages API keys, model selections, laptop resource thresholds, and operational defaults.
"""

import os
from pathlib import Path
from typing import List

# Base Paths
BASE_DIR = Path(__file__).parent.resolve()
DATA_DIR = BASE_DIR / "data"
DELIVERABLES_DIR = BASE_DIR / "deliverables"
STATIC_DIR = BASE_DIR / "static"

for directory in [DATA_DIR, DELIVERABLES_DIR, STATIC_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "microcorp.db"

# Find Gemini API Key
def get_gemini_api_key() -> str:
    # 1. Environment variable
    if os.environ.get("GEMINI_API_KEY"):
        return os.environ["GEMINI_API_KEY"].strip()
    
    # 2. Local .env
    local_env = BASE_DIR / ".env"
    if local_env.exists():
        with open(local_env, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip().startswith("GEMINI_API_KEY="):
                    return line.strip().split("=", 1)[1].strip().strip('"').strip("'")
                    
    # 3. Known agent .env files on this system
    fallback_envs = [
        Path("/media/alpesh/Software & Work/Agents/book-publishing-agent/.env"),
        Path("/media/alpesh/Software & Work/Agents/apk-tv-converter-agent/.env"),
        Path("/media/alpesh/Software & Work/Agents/jarvis-agent/.env"),
    ]
    for env_path in fallback_envs:
        if env_path.exists():
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip().startswith("GEMINI_API_KEY="):
                            return line.strip().split("=", 1)[1].strip().strip('"').strip("'")
            except Exception:
                continue
    return ""

GEMINI_API_KEY = get_gemini_api_key()

# LLM Model Hierarchy with automatic fallback
LLM_MODELS: List[str] = [
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-flash-lite-latest",
    "gemini-3.5-flash",
    "gemini-3.8-flash",
]

# Company Operational Settings
COMPANY_NAME = "MicroCorp AI"
COMPANY_TAGLINE = "Autonomous Laptop Enterprise"
CEO_NAME = "Artemis (Executive Core)"

# Laptop Safety & Resource Guardian Thresholds
MAX_CPU_PERCENT = 90.0          # Pause / throttle workers if CPU exceeds this
MAX_MEMORY_PERCENT = 94.0       # Pause / throttle workers if RAM exceeds this
MIN_BATTERY_PERCENT = 15.0      # Pause non-urgent tasks if on battery below 15%
LOOP_INTERVAL_SECONDS = 10      # Main CEO orchestrator loop cycle time

# Dynamic Scaling Thresholds
QUEUE_THRESHOLD_FOR_SUBAGENT = 2 # If domain queue has >= 2 pending tasks, spawn subagent
MAX_SUBAGENTS_PER_DEPT = 4       # Max parallel worker subagents per department
MAX_TOTAL_SUBAGENTS = 12         # Laptop guard limit for simultaneous subagents
IDLE_TIMEOUT_MINUTES = 5         # Auto-reap subagents after 5 minutes of idle time

# Server & Dashboard Settings
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8585
AUTONOMY_MODE = "autonomous"     # "autonomous" (self-executing) or "supervised"
AUTO_SPRINT_INTERVAL_MINUTES = 5 # Automatically triggers self-directed income sprints every 5 minutes
MAX_AUTO_SPRINTS_PER_DAY = 96    # Scaled capacity for continuous background production
ENABLE_AUTO_HARVEST = True       # Continuously discover and execute online opportunities

# Real-World Passive Income & UPI Payout Gateway
PAYOUT_UPI_ID = os.environ.get("PAYOUT_UPI_ID", "talpesh100@ybl")
PAYEE_NAME = os.environ.get("PAYEE_NAME", "Alpesh Thakor")
WHATSAPP_NUMBER = os.environ.get("WHATSAPP_NUMBER", "919999999999")
CONTACT_EMAIL = os.environ.get("CONTACT_EMAIL", "talpesh100@ybl")
DEFAULT_CURRENCY = "INR"
USD_TO_INR_RATE = 86.50          # Benchmark exchange rate for international pricing

# Public Cloudflare Tunnel & Distribution Gateway
CLOUDFLARED_BIN = Path("/home/alpesh/bin/cloudflared")
GH_BIN = Path("/home/alpesh/.local/bin/gh")
ENABLE_PUBLIC_TUNNEL = True
ENABLE_GITHUB_RELEASES = True
GITHUB_REPO = "thakoralpesh3/microcorp-agent"
PUBLIC_GATEWAY_FILE = DATA_DIR / "public_gateway.json"
PUBLIC_QR_FILE = DATA_DIR / "public_store_qr.svg"



