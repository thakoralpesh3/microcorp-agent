#!/usr/bin/env bash
# MicroCorp AI - Startup Script
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================================="
echo "  🚀 Starting MicroCorp AI Autonomous Enterprise..."
echo "  🏢 Running locally on your laptop"
echo "  📊 Web Console: http://127.0.0.1:8585"
echo "=========================================================="

python3 app.py --port 8585 --host 127.0.0.1
