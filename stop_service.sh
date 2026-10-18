#!/usr/bin/env bash
# Stop MicroCorp AI Background Service
pkill -f "app.py.*8585" 2>/dev/null || true
notify-send "MicroCorp AI" "Enterprise background service stopped." 2>/dev/null || true
