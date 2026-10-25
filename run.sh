#!/usr/bin/env bash
# ==============================================================================
# MicroCorp AI - Universal One-Command Startup Script (GitHub Clones & Local)
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================================="
echo "  🏢 MicroCorp AI — Autonomous Laptop Enterprise"
echo "  👑 Executive Core: Artemis (Executive Core)"
echo "  🌐 Dashboard URL:  http://127.0.0.1:8585"
echo "  💳 Beneficiary:    talpesh100@ybl (Alpesh Thakor)"
echo "=========================================================="

# 1. Ensure .env exists (copy from .env.example if missing)
if [ ! -f ".env" ] && [ -f ".env.example" ]; then
    echo "📋 Initializing .env configuration from .env.example..."
    cp .env.example .env
fi

# 2. Check for Python 3
PYTHON_BIN=""
if command -v python3 &>/dev/null; then
    PYTHON_BIN="python3"
elif command -v python &>/dev/null; then
    PYTHON_BIN="python"
else
    echo "❌ Error: Python 3 is not installed. Please install Python 3.10+."
    exit 1
fi

# 3. Check / install dependencies if needed
if ! "$PYTHON_BIN" -c "import fastapi, uvicorn, pydantic, qrcode, httpx" &>/dev/null; then
    echo "📦 Required packages missing. Installing from requirements.txt..."
    "$PYTHON_BIN" -m pip install -r requirements.txt
fi

# 4. Check if port 8585 is already in use
if "$PYTHON_BIN" -c "import socket; s = socket.socket(); s.settimeout(1); exit(0 if s.connect_ex(('127.0.0.1', 8585)) == 0 else 1)" &>/dev/null; then
    echo "ℹ️  Server is already running on port 8585."
    echo "👉 Opening dashboard: http://127.0.0.1:8585"
    if command -v xdg-open &>/dev/null; then
        xdg-open "http://127.0.0.1:8585" 2>/dev/null || true
    fi
    exit 0
fi

# 5. Launch Enterprise Server
echo "🚀 Launching MicroCorp AI Enterprise..."
exec "$PYTHON_BIN" app.py --port 8585 --host 127.0.0.1
