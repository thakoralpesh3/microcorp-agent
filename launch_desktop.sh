#!/usr/bin/env bash
# MicroCorp AI - Desktop One-Click Launcher
set -e

DIR="/media/alpesh/Software & Work/Agents/microcorp-agent"
cd "$DIR"

# Check if server is already responding on port 8585
if ! curl -s --head --request GET http://127.0.0.1:8585 | grep "200 OK" > /dev/null; then
    # Start app.py in background if not already running
    nohup python3 app.py --port 8585 --host 127.0.0.1 > "$DIR/data/app.log" 2>&1 &
    PID=$!
    echo $PID > "$DIR/data/server.pid"
    disown $PID 2>/dev/null || true
    
    # Wait for server to come online
    for i in {1..10}; do
        sleep 0.5
        if curl -s http://127.0.0.1:8585/api/telemetry > /dev/null 2>&1; then
            break
        fi
    done
fi

# Send Desktop Notification
notify-send -i "$DIR/static/icon.svg" "MicroCorp AI Online" "Autonomous Laptop Enterprise active at http://127.0.0.1:8585" 2>/dev/null || true

# Open dashboard in default browser
xdg-open "http://127.0.0.1:8585" 2>/dev/null || sensible-browser "http://127.0.0.1:8585" 2>/dev/null || firefox "http://127.0.0.1:8585" 2>/dev/null &
