@echo off
REM ==============================================================================
REM MicroCorp AI - Universal Startup Script for Windows
REM ==============================================================================
TITLE MicroCorp AI Enterprise

echo ==========================================================
echo   🏢 MicroCorp AI — Autonomous Laptop Enterprise
echo   👑 Executive Core: Artemis (Executive Core)
echo   🌐 Dashboard URL:  http://127.0.0.1:8585
echo   💳 Beneficiary:    talpesh100@ybl (Alpesh Thakor)
echo ==========================================================

REM 1. Copy .env from .env.example if missing
if not exist .env (
    if exist .env.example (
        echo 📋 Initializing .env configuration from .env.example...
        copy .env.example .env >nul
    )
)

REM 2. Check for Python
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ❌ Python is not detected in PATH. Please install Python 3.10+ and add it to PATH.
    pause
    exit /b 1
)

REM 3. Install dependencies if needed
python -c "import fastapi, uvicorn, pydantic, qrcode, httpx" >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo 📦 Installing dependencies from requirements.txt...
    python -m pip install -r requirements.txt
)

REM 4. Launch Enterprise Server
echo 🚀 Launching MicroCorp AI Enterprise...
start http://127.0.0.1:8585
python app.py --port 8585 --host 127.0.0.1
pause
