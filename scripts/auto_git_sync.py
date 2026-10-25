#!/usr/bin/env python3
"""
MicroCorp AI — Autonomous Antigravity GitHub Sync Daemon
Monitors the repository for any code or asset modifications made by Antigravity
or autonomous departmental subagents and automatically stages, commits, and pushes
them to GitHub origin main.
"""

import os
import sys
import time
import shutil
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

def get_git_env() -> dict:
    env = os.environ.copy()
    user_home = str(Path.home())
    env["PATH"] = f"{user_home}/.local/bin:{env.get('PATH', '')}:/usr/local/bin:/usr/bin:/bin"
    env["HOME"] = user_home
    return env

def run_git(args: list[str]) -> tuple[int, str]:
    git_bin = shutil.which("git") or str(Path.home() / ".local/bin/git")
    res = subprocess.run(
        [git_bin] + args,
        cwd=str(REPO_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=get_git_env()
    )
    return res.returncode, (res.stdout + res.stderr).strip()

def sync_now(custom_msg: str = None) -> bool:
    """Stages all changes, commits, and pushes to GitHub."""
    code, status = run_git(["status", "--porcelain"])
    if not status:
        return True

    print(f"[{time.strftime('%X')}] 📦 Local file changes detected by Antigravity Watchdog...")
    run_git(["add", "-A"])

    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    msg = custom_msg or f"🤖 Auto-Sync: Antigravity update in MicroCorp AI Autonomous Enterprise [{timestamp}]"
    code, out = run_git(["commit", "-m", msg])
    if code != 0:
        print(f"[{time.strftime('%X')}] Commit failed: {out}")
        return False

    code, branch = run_git(["branch", "--show-current"])
    branch_name = branch.strip() or "main"

    print(f"[{time.strftime('%X')}] 🚀 Pushing to origin/{branch_name}...")
    code, out = run_git(["push", "origin", branch_name])
    if code == 0:
        code, commit_hash = run_git(["rev-parse", "--short", "HEAD"])
        print(f"[{time.strftime('%X')}] ✅ Successfully synced to GitHub! ({commit_hash})")
        return True
    else:
        # If push failed, try pull --rebase then push again
        print(f"[{time.strftime('%X')}] ⚠️ Direct push failed, attempting pull --rebase: {out}")
        rcode, rout = run_git(["pull", "--rebase", "origin", branch_name])
        if rcode == 0:
            pcode, pout = run_git(["push", "origin", branch_name])
            if pcode == 0:
                print(f"[{time.strftime('%X')}] ✅ Rebase and push succeeded!")
                return True
        print(f"[{time.strftime('%X')}] ❌ Push failed: {out}")
        return False

def run_polling_sync(interval_sec: int = 15):
    """Continuous polling loop watching for Antigravity edits."""
    print(f"🔍 Starting MicroCorp Antigravity Auto-Sync Watcher (polling every {interval_sec}s)...")
    dirty_counter = 0

    while True:
        try:
            code, status = run_git(["status", "--porcelain"])
            is_dirty = bool(status.strip())

            if is_dirty:
                dirty_counter += 1
                # Wait 2 consecutive checks (debounce ~30s) to allow Antigravity to finish writing
                if dirty_counter >= 2:
                    sync_now()
                    dirty_counter = 0
            else:
                dirty_counter = 0

            time.sleep(interval_sec)
        except KeyboardInterrupt:
            print("\nStopped Auto-Sync Watcher.")
            break
        except Exception as e:
            print(f"Auto-Sync exception: {e}")
            time.sleep(interval_sec)

if __name__ == "__main__":
    if "--now" in sys.argv:
        msg = sys.argv[2] if len(sys.argv) > 2 else None
        success = sync_now(msg)
        sys.exit(0 if success else 1)
    else:
        run_polling_sync(15)
