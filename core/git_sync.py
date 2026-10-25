"""
MicroCorp AI - GitHub Synchronization Engine
Automates two-way synchronization between local laptop execution and GitHub:
- Tracks local code, department states, and deliverable changes
- Automatically stages, commits, and pushes to remote GitHub repository
- Reports repository sync status, commit history, and remote connectivity
"""

import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

PROJECT_ROOT = Path(__file__).parent.parent.resolve()

class GitSyncEngine:
    def __init__(self, repo_dir: Path = PROJECT_ROOT):
        self.repo_dir = repo_dir
        self.remote_name = "origin"
        self.default_branch = "main"

    def _run_git(self, args: list, timeout: int = 30) -> subprocess.CompletedProcess:
        """Runs a git command inside the repository directory."""
        return subprocess.run(
            ["git"] + args,
            cwd=str(self.repo_dir),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False
        )

    def is_git_repo(self) -> bool:
        """Returns True if the directory is a valid git repository."""
        res = self._run_git(["rev-parse", "--is-inside-work-tree"])
        return res.returncode == 0 and res.stdout.strip() == "true"

    def get_remote_url(self) -> Optional[str]:
        """Returns the configured remote URL for origin, or None."""
        res = self._run_git(["remote", "get-url", self.remote_name])
        if res.returncode == 0:
            return res.stdout.strip()
        return None

    def get_current_branch(self) -> str:
        """Returns the active git branch."""
        res = self._run_git(["rev-parse", "--abbrev-ref", "HEAD"])
        return res.stdout.strip() if res.returncode == 0 else "main"

    def get_last_commit(self) -> Dict[str, str]:
        """Returns details about the HEAD commit."""
        res = self._run_git(["log", "-1", "--format=%H|%s|%an|%ad", "--date=iso"])
        if res.returncode == 0 and res.stdout.strip():
            parts = res.stdout.strip().split("|")
            if len(parts) >= 4:
                return {
                    "hash": parts[0][:8],
                    "full_hash": parts[0],
                    "subject": parts[1],
                    "author": parts[2],
                    "date": parts[3]
                }
        return {"hash": "none", "subject": "No commits", "author": "", "date": ""}

    def get_sync_status(self) -> Dict[str, Any]:
        """
        Gathers comprehensive sync status between local workspace and GitHub.
        """
        if not self.is_git_repo():
            return {
                "is_git_repo": False,
                "error": "Not a git repository"
            }

        remote_url = self.get_remote_url()
        branch = self.get_current_branch()
        last_commit = self.get_last_commit()

        # Check working tree status
        status_res = self._run_git(["status", "--porcelain"])
        changed_files = [line.strip() for line in status_res.stdout.splitlines() if line.strip()]
        is_clean = len(changed_files) == 0

        # Check ahead/behind status against origin
        ahead = 0
        behind = 0
        try:
            rev_res = self._run_git(["rev-list", "--left-right", "--count", f"{branch}...{self.remote_name}/{branch}"])
            if rev_res.returncode == 0 and rev_res.stdout.strip():
                parts = rev_res.stdout.strip().split()
                if len(parts) == 2:
                    ahead = int(parts[0])
                    behind = int(parts[1])
        except Exception:
            pass

        return {
            "is_git_repo": True,
            "branch": branch,
            "remote_url": remote_url,
            "is_clean": is_clean,
            "changed_files_count": len(changed_files),
            "changed_files": changed_files[:10],
            "ahead": ahead,
            "behind": behind,
            "last_commit": last_commit,
            "last_checked": datetime.now().isoformat()
        }

    def sync_to_github(self, commit_message: Optional[str] = None) -> Dict[str, Any]:
        """
        Automatically stages changes, commits them with an informative message,
        and pushes to the GitHub remote repository.
        """
        if not self.is_git_repo():
            return {"success": False, "error": "Not a git repository"}

        # 1. Check if there are changes to stage
        status_res = self._run_git(["status", "--porcelain"])
        raw_status = status_res.stdout.strip()

        pushed = False
        commit_created = False
        commit_info = {}

        if raw_status:
            # Stage all changes (excluding ignored files in .gitignore)
            add_res = self._run_git(["add", "-A"])
            if add_res.returncode != 0:
                return {
                    "success": False,
                    "error": f"git add failed: {add_res.stderr.strip()}"
                }

            # Generate default commit message if none provided
            if not commit_message:
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                commit_message = f"auto: autonomous enterprise sync deliverables & state [{ts}]"

            # Create commit
            commit_res = self._run_git(["commit", "-m", commit_message])
            if commit_res.returncode != 0:
                return {
                    "success": False,
                    "error": f"git commit failed: {commit_res.stderr.strip()}"
                }
            commit_created = True

        # 2. Check if we have unpushed commits
        branch = self.get_current_branch()
        push_res = self._run_git(["push", self.remote_name, branch], timeout=60)
        if push_res.returncode == 0:
            pushed = True
        else:
            # If push failed, try pulling rebase if remote has new commits
            rebase_res = self._run_git(["pull", "--rebase", self.remote_name, branch], timeout=60)
            if rebase_res.returncode == 0:
                retry_push = self._run_git(["push", self.remote_name, branch], timeout=60)
                pushed = (retry_push.returncode == 0)
            else:
                return {
                    "success": False,
                    "committed": commit_created,
                    "pushed": False,
                    "error": f"Push failed: {push_res.stderr.strip()}"
                }

        latest_commit = self.get_last_commit()

        return {
            "success": True,
            "committed": commit_created,
            "pushed": pushed,
            "branch": branch,
            "commit": latest_commit,
            "message": "Repository successfully synchronized with GitHub."
        }

# Singleton instance
git_sync = GitSyncEngine()
