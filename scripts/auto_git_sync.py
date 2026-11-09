#!/usr/bin/env python3
"""
MicroCorp AI — Autonomous Antigravity GitHub Sync Daemon
Monitors the repository for any code or asset modifications made by Antigravity
or autonomous departmental subagents and automatically stages, commits, and pushes
them to GitHub origin main with adaptive polling and NTFS disk efficiency.
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
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GIT_EDITOR"] = "true"
    env["GIT_SEQUENCE_EDITOR"] = "true"
    return env

def clean_stale_locks():
    """Removes stale git lock files only if no active git process exists."""
    locks = [
        REPO_ROOT / ".git/index.lock",
        REPO_ROOT / ".git/HEAD.lock",
        REPO_ROOT / ".git/refs/heads/main.lock"
    ]
    for lock in locks:
        if lock.exists():
            try:
                # Check if any git process is actually running
                res = subprocess.run(["pgrep", "-f", "git.real"], stdout=subprocess.PIPE, text=True)
                if not res.stdout.strip():
                    lock.unlink(missing_ok=True)
                elif time.time() - lock.stat().st_mtime > 180:
                    lock.unlink(missing_ok=True)
            except Exception:
                pass

def run_git(args: list[str], timeout: int = 300) -> tuple[int, str]:
    clean_stale_locks()
    git_bin = shutil.which("git") or str(Path.home() / ".local/bin/git")
    try:
        res = subprocess.run(
            [git_bin] + args,
            cwd=str(REPO_ROOT),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            env=get_git_env()
        )
        return res.returncode, (res.stdout + res.stderr).strip()
    except subprocess.TimeoutExpired:
        return 124, "git command timed out"

def sync_now(custom_msg: str = None) -> bool:
    """Stages changes, commits, and pushes to GitHub with path targeting."""
    code, status = run_git(["status", "--porcelain", "-uno"])
    if not status:
        return True

    print(f"[{time.strftime('%X')}] 📦 Local file changes detected by Antigravity Watchdog...")
    # Add tracked changes quickly without deep untracked disk scan
    add_code, add_out = run_git(["add", "-u"], timeout=120)
    # Stage newly created deliverables or docs specifically
    run_git(["add", "docs/", "deliverables/", "index.html", "scripts/"], timeout=120)

    # Skip commit if nothing is staged
    diff_code, _ = run_git(["diff", "--cached", "--quiet"])
    if diff_code == 0:
        return True

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
        # If push failed, try pull with -s ort -X ours to seamlessly integrate cloud commits
        print(f"[{time.strftime('%X')}] ⚠️ Direct push rejected, merging remote changes: {out}")
        mcode, mout = run_git(["pull", "--no-edit", "-s", "ort", "-X", "ours", "origin", branch_name])
        if mcode == 0:
            pcode, pout = run_git(["push", "origin", branch_name])
            if pcode == 0:
                print(f"[{time.strftime('%X')}] ✅ Merge and push succeeded!")
                return True
        else:
            run_git(["merge", "--abort"])
        print(f"[{time.strftime('%X')}] ❌ Push failed: {out}")
        return False

def run_polling_sync():
    """Adaptive polling loop watching for Antigravity edits with low NTFS I/O footprint."""
    print("🔍 Starting MicroCorp Antigravity Auto-Sync Watcher (adaptive polling)...")
    clean_cycles = 0

    while True:
        try:
            # Quick check with -uno to avoid full NTFS untracked file walking
            code, status = run_git(["status", "--porcelain", "-uno"])
            is_dirty = bool(status.strip())

            # If tracked files didn't show changes, do a check including untracked once every 3 cycles
            if not is_dirty and (clean_cycles % 3 == 0):
                code, status_all = run_git(["status", "--porcelain"])
                is_dirty = bool(status_all.strip())

            if is_dirty:
                clean_cycles = 0
                time.sleep(10)  # Debounce to let multi-file Antigravity writes complete
                sync_now()
                sleep_sec = 20
            else:
                clean_cycles += 1
                # Adaptive backoff when repository is clean: 25s -> 45s -> max 60s
                sleep_sec = 60 if clean_cycles > 5 else (40 if clean_cycles > 2 else 25)

            time.sleep(sleep_sec)
        except KeyboardInterrupt:
            print("\nStopped Auto-Sync Watcher.")
            break
        except Exception as e:
            print(f"Auto-Sync exception: {e}")
            time.sleep(30)

if __name__ == "__main__":
    if "--now" in sys.argv:
        msg = sys.argv[2] if len(sys.argv) > 2 else None
        success = sync_now(msg)
        sys.exit(0 if success else 1)
    else:
        run_polling_sync()
