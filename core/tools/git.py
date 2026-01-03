"""
Git Tools
=========
Git operations for agentic coding workflows.
"""

import subprocess
from pathlib import Path
from typing import Any, List, Optional

from agno.tools import tool

from ..policies import AgentSpec


def _run_git_command(
    args: List[str],
    cwd: str,
    timeout: int = 30,
) -> dict:
    """Run a git command and return result."""
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip() if result.returncode != 0 else None,
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Command timed out"}
    except FileNotFoundError:
        return {"success": False, "error": "Git is not installed"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def build_git_tools(spec: AgentSpec) -> List[Any]:
    """
    Build git tools based on spec configuration.

    Tools:
    - git_status: Show working tree status
    - git_diff: Show changes in files
    - git_log: Show commit history
    - git_branch: List or manage branches
    - git_add: Stage files for commit
    - git_commit: Create a commit (if allowed)
    - git_show: Show commit details

    Args:
        spec: Agent specification with coding policy

    Returns:
        List of git tools
    """
    if not spec.coding.enabled or not spec.coding.enable_git:
        return []

    workspace_root = spec.coding.workspace_root

    @tool
    def git_status(short: bool = False) -> dict:
        """
        Show the working tree status.

        Args:
            short: Use short format output

        Returns:
            Dict with status information
        """
        args = ["status"]
        if short:
            args.append("--short")
        else:
            args.append("--porcelain=v1")
        
        result = _run_git_command(args, workspace_root)
        
        if not result["success"]:
            return result
        
        if short or "--porcelain" in str(args):
            lines = result["stdout"].split("\n") if result["stdout"] else []
            changes = []
            for line in lines:
                if line.strip():
                    status = line[:2]
                    filepath = line[3:]
                    changes.append({"status": status, "file": filepath})
            return {
                "success": True,
                "changes": changes,
                "clean": len(changes) == 0,
            }
        
        return result

    @tool
    def git_diff(
        path: Optional[str] = None,
        staged: bool = False,
        commit: Optional[str] = None,
    ) -> dict:
        """
        Show changes between commits, commit and working tree, etc.

        Args:
            path: Specific file or directory to diff
            staged: Show staged changes (--cached)
            commit: Compare with specific commit

        Returns:
            Dict with diff output
        """
        args = ["diff", "--no-color"]
        
        if staged:
            args.append("--cached")
        
        if commit:
            args.append(commit)
        
        if path:
            args.extend(["--", path])
        
        result = _run_git_command(args, workspace_root)
        
        if result["success"]:
            return {
                "success": True,
                "diff": result["stdout"],
                "has_changes": bool(result["stdout"]),
            }
        
        return result

    @tool
    def git_log(
        max_count: int = 10,
        oneline: bool = True,
        path: Optional[str] = None,
    ) -> dict:
        """
        Show commit history.

        Args:
            max_count: Maximum number of commits to show
            oneline: Use one-line format
            path: Show history for specific file

        Returns:
            Dict with commit history
        """
        args = ["log", f"-n{max_count}"]
        
        if oneline:
            args.append("--oneline")
        else:
            args.append("--format=%H|%an|%ae|%s|%ai")
        
        if path:
            args.extend(["--", path])
        
        result = _run_git_command(args, workspace_root)
        
        if not result["success"]:
            return result
        
        if oneline:
            lines = result["stdout"].split("\n") if result["stdout"] else []
            commits = []
            for line in lines:
                if line.strip():
                    parts = line.split(" ", 1)
                    commits.append({
                        "hash": parts[0],
                        "message": parts[1] if len(parts) > 1 else "",
                    })
            return {"success": True, "commits": commits}
        else:
            lines = result["stdout"].split("\n") if result["stdout"] else []
            commits = []
            for line in lines:
                if line.strip():
                    parts = line.split("|")
                    if len(parts) >= 5:
                        commits.append({
                            "hash": parts[0],
                            "author": parts[1],
                            "email": parts[2],
                            "message": parts[3],
                            "date": parts[4],
                        })
            return {"success": True, "commits": commits}

    @tool
    def git_branch(
        list_all: bool = False,
        list_remote: bool = False,
    ) -> dict:
        """
        List branches.

        Args:
            list_all: List both local and remote branches
            list_remote: List only remote branches

        Returns:
            Dict with branch information
        """
        args = ["branch", "--no-color"]
        
        if list_all:
            args.append("-a")
        elif list_remote:
            args.append("-r")
        
        result = _run_git_command(args, workspace_root)
        
        if not result["success"]:
            return result
        
        lines = result["stdout"].split("\n") if result["stdout"] else []
        branches = []
        current = None
        
        for line in lines:
            if line.strip():
                is_current = line.startswith("*")
                name = line.lstrip("* ").strip()
                branches.append(name)
                if is_current:
                    current = name
        
        return {
            "success": True,
            "branches": branches,
            "current": current,
        }

    @tool
    def git_show(commit: str = "HEAD", stat_only: bool = False) -> dict:
        """
        Show commit details.

        Args:
            commit: Commit hash or reference (default: HEAD)
            stat_only: Show only file statistics, not full diff

        Returns:
            Dict with commit information
        """
        args = ["show", "--no-color", commit]
        
        if stat_only:
            args.append("--stat")
        
        result = _run_git_command(args, workspace_root)
        
        return result

    @tool
    def git_add(paths: List[str], all_changes: bool = False) -> dict:
        """
        Stage files for commit.

        Args:
            paths: List of file paths to stage
            all_changes: Stage all changes (-A)

        Returns:
            Dict with success status
        """
        if not spec.coding.allow_git_write:
            return {"error": "Git write operations are disabled"}
        
        if all_changes:
            args = ["add", "-A"]
        else:
            if not paths:
                return {"error": "No paths specified"}
            args = ["add"] + paths
        
        result = _run_git_command(args, workspace_root)
        
        if result["success"]:
            return {"success": True, "staged": paths if not all_changes else "all"}
        
        return result

    @tool
    def git_commit(message: str, amend: bool = False) -> dict:
        """
        Create a commit with staged changes.

        Args:
            message: Commit message
            amend: Amend the previous commit

        Returns:
            Dict with commit information
        """
        if not spec.coding.allow_git_write:
            return {"error": "Git write operations are disabled"}
        
        if not message.strip():
            return {"error": "Commit message cannot be empty"}
        
        args = ["commit", "-m", message]
        
        if amend:
            args.append("--amend")
        
        result = _run_git_command(args, workspace_root)
        
        if result["success"]:
            hash_result = _run_git_command(["rev-parse", "HEAD"], workspace_root)
            return {
                "success": True,
                "message": message,
                "hash": hash_result["stdout"][:8] if hash_result["success"] else None,
            }
        
        return result

    @tool
    def git_blame(path: str, start_line: Optional[int] = None, end_line: Optional[int] = None) -> dict:
        """
        Show what revision and author last modified each line of a file.

        Args:
            path: File path to blame
            start_line: Starting line number
            end_line: Ending line number

        Returns:
            Dict with blame information
        """
        args = ["blame", "--porcelain"]
        
        if start_line and end_line:
            args.extend(["-L", f"{start_line},{end_line}"])
        
        args.append(path)
        
        result = _run_git_command(args, workspace_root)
        
        if not result["success"]:
            return result
        
        return {
            "success": True,
            "blame": result["stdout"],
        }

    tools = [
        git_status,
        git_diff,
        git_log,
        git_branch,
        git_show,
        git_blame,
    ]
    
    if spec.coding.allow_git_write:
        tools.extend([git_add, git_commit])
    
    return tools
