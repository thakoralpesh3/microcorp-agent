#!/usr/bin/env bash
# MicroCorp AI - Instant Antigravity & Enterprise GitHub Two-Way Synchronizer
# Automatically stages all Antigravity & local code changes, commits, and pushes to origin main.
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

COMMIT_MSG="${1:-auto: sync antigravity updates and enterprise state [$(date +'%Y-%m-%d %H:%M:%S')]}"

echo "=========================================================="
echo "  🔄 MicroCorp AI -> GitHub Two-Way Synchronizer"
echo "  🏢 Repository: $(git remote get-url origin 2>/dev/null || echo 'origin')"
echo "  🌿 Branch: $(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo 'main')"
echo "  📌 Message: $COMMIT_MSG"
echo "=========================================================="

python3 -c "
import sys
from core.git_sync import git_sync
result = git_sync.sync_to_github('''$COMMIT_MSG''')
print('Sync Result:', result)
if not result.get('success'):
    sys.exit(1)
"

echo "=========================================================="
echo "  ✅ GitHub synchronization completed successfully!"
echo "  🎯 Current commit: $(git rev-parse --short HEAD)"
echo "=========================================================="
