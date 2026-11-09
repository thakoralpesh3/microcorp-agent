"""
MicroCorp AI - Continuous Antigravity & Enterprise Git Auto-Syncer
Runs as a background daemon thread to detect local file changes and sync to GitHub.
If the dedicated microcorp-sync systemd service (auto_git_sync.py) is active,
it delegates routine polling to avoid duplicate git index locking.
"""

import os
import time
import threading
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from core.git_sync import git_sync

logger = logging.getLogger("MicroCorp.GitAutoSyncer")

class GitAutoSyncer:
    def __init__(self, check_interval_seconds: int = 60):
        self.interval = check_interval_seconds
        self.is_running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self.last_sync_time: Optional[str] = None
        self.last_sync_result: Optional[Dict[str, Any]] = None

    def _is_external_syncer_running(self) -> bool:
        """Checks if auto_git_sync.py is already active as a daemon."""
        try:
            import psutil
            cur_pid = os.getpid()
            for p in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if p.info['pid'] != cur_pid and p.info['cmdline']:
                        cmd_str = " ".join(p.info['cmdline'])
                        if "auto_git_sync.py" in cmd_str:
                            return True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception:
            pass
        return False

    def start(self):
        """Starts the background auto-sync thread."""
        with self._lock:
            if self.is_running:
                return
            self.is_running = True
            self._thread = threading.Thread(target=self._sync_loop, daemon=True, name="Antigravity-GitAutoSync")
            self._thread.start()
            logger.info(f"🔄 Antigravity Git Auto-Syncer active (Interval: {self.interval}s).")

    def stop(self):
        """Stops the auto-sync daemon."""
        with self._lock:
            self.is_running = False
            logger.info("🛑 Antigravity Git Auto-Syncer stopped.")

    def trigger_sync(self, reason: str = "antigravity update") -> Dict[str, Any]:
        """Manually or programmatically triggers an immediate synchronization to GitHub."""
        try:
            status = git_sync.get_sync_status()
            if not status.get("is_git_repo"):
                return {"synced": False, "reason": "Not a git repository"}

            if not status.get("is_clean") or status.get("ahead", 0) > 0:
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                msg = f"auto: {reason} [{ts}]"
                logger.info(f"🚀 Antigravity Auto-Syncer: syncing changes to GitHub: {msg}...")
                res = git_sync.sync_to_github(commit_message=msg)
                self.last_sync_time = ts
                self.last_sync_result = res
                return {"synced": True, "result": res}
            else:
                return {"synced": False, "message": "Working tree clean, already up to date with GitHub."}
        except Exception as e:
            logger.warning(f"Git auto-sync error: {e}")
            return {"synced": False, "error": str(e)}

    def _sync_loop(self):
        """Daemon loop checking for file changes and auto-pushing to GitHub."""
        time.sleep(10)  # Initial grace period upon startup
        while self.is_running:
            try:
                # If the external dedicated systemd sync daemon is active, avoid conflicting git operations
                if self._is_external_syncer_running():
                    logger.debug("External auto_git_sync daemon active; routine sync delegated.")
                else:
                    self.trigger_sync(reason="antigravity auto-sync cycle")
            except Exception as e:
                logger.debug(f"Auto-sync loop exception: {e}")
            time.sleep(self.interval)

# Global singleton
auto_syncer = GitAutoSyncer()
