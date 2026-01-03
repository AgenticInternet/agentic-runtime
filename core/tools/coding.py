"""
Agentic Coding Tools
====================
File manipulation and code search tools for agentic coding workflows.
"""

import os
import re
from pathlib import Path
from typing import Any, List, Optional

from agno.tools import tool

from ..policies import AgentSpec


def _validate_path(path: str, workspace_root: str) -> Path:
    """Validate path is within workspace and return resolved Path."""
    resolved = Path(path).resolve()
    workspace = Path(workspace_root).resolve()

    if not str(resolved).startswith(str(workspace)):
        raise ValueError(f"Path {path} is outside workspace root {workspace_root}")

    return resolved


def _is_binary_file(path: Path) -> bool:
    """Check if a file is binary."""
    try:
        with open(path, "rb") as f:
            chunk = f.read(8192)
            return b"\x00" in chunk
    except Exception:
        return True


def build_coding_tools(spec: AgentSpec) -> List[Any]:
    """
    Build coding tools based on spec configuration.

    Tools:
    - read_file: Read file contents with optional line range
    - write_file: Write/create file with content
    - edit_file: Edit file by replacing text
    - list_directory: List directory contents
    - find_files: Find files matching glob pattern
    - grep: Search for text patterns in files
    - get_file_info: Get file metadata

    Args:
        spec: Agent specification with coding policy

    Returns:
        List of coding tools
    """
    if not spec.coding.enabled:
        return []

    workspace_root = spec.coding.workspace_root
    max_file_size = spec.coding.max_file_size_kb * 1024
    max_results = spec.coding.max_search_results

    @tool
    def read_file(
        path: str,
        start_line: Optional[int] = None,
        end_line: Optional[int] = None,
    ) -> dict:
        """
        Read file contents with optional line range.

        Args:
            path: Path to file (absolute or relative to workspace)
            start_line: Starting line number (1-indexed, inclusive)
            end_line: Ending line number (1-indexed, inclusive)

        Returns:
            Dict with content, line_count, and path
        """
        try:
            if not os.path.isabs(path):
                path = os.path.join(workspace_root, path)

            file_path = _validate_path(path, workspace_root)

            if not file_path.exists():
                return {"error": f"File not found: {path}"}

            if not file_path.is_file():
                return {"error": f"Not a file: {path}"}

            if file_path.stat().st_size > max_file_size:
                return {"error": f"File too large (max {spec.coding.max_file_size_kb}KB)"}

            if _is_binary_file(file_path):
                return {"error": "Cannot read binary file"}

            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()

            total_lines = len(lines)

            if start_line is not None or end_line is not None:
                start = (start_line or 1) - 1
                end = end_line or total_lines
                lines = lines[max(0, start):min(total_lines, end)]

            numbered_lines = [
                f"{i + (start_line or 1)}: {line.rstrip()}"
                for i, line in enumerate(lines)
            ]

            return {
                "content": "\n".join(numbered_lines),
                "line_count": total_lines,
                "path": str(file_path),
                "lines_shown": len(lines),
            }
        except Exception as e:
            return {"error": str(e)}

    @tool
    def write_file(path: str, content: str, create_directories: bool = True) -> dict:
        """
        Write content to a file (creates or overwrites).

        Args:
            path: Path to file (absolute or relative to workspace)
            content: Content to write
            create_directories: Create parent directories if needed

        Returns:
            Dict with success status and path
        """
        if not spec.coding.allow_write:
            return {"error": "Write operations are disabled"}

        try:
            if not os.path.isabs(path):
                path = os.path.join(workspace_root, path)

            file_path = _validate_path(path, workspace_root)

            if create_directories:
                file_path.parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            return {
                "success": True,
                "path": str(file_path),
                "bytes_written": len(content.encode("utf-8")),
            }
        except Exception as e:
            return {"error": str(e)}

    @tool
    def edit_file(
        path: str,
        old_text: str,
        new_text: str,
        replace_all: bool = False,
    ) -> dict:
        """
        Edit a file by replacing text.

        Args:
            path: Path to file (absolute or relative to workspace)
            old_text: Text to find and replace
            new_text: Replacement text
            replace_all: Replace all occurrences (default: first only)

        Returns:
            Dict with success status, replacements made, and diff preview
        """
        if not spec.coding.allow_write:
            return {"error": "Write operations are disabled"}

        try:
            if not os.path.isabs(path):
                path = os.path.join(workspace_root, path)

            file_path = _validate_path(path, workspace_root)

            if not file_path.exists():
                return {"error": f"File not found: {path}"}

            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            if old_text not in content:
                return {"error": "Text not found in file"}

            if replace_all:
                new_content = content.replace(old_text, new_text)
                count = content.count(old_text)
            else:
                new_content = content.replace(old_text, new_text, 1)
                count = 1

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_content)

            return {
                "success": True,
                "path": str(file_path),
                "replacements": count,
            }
        except Exception as e:
            return {"error": str(e)}

    @tool
    def list_directory(path: str = ".", show_hidden: bool = False) -> dict:
        """
        List contents of a directory.

        Args:
            path: Directory path (absolute or relative to workspace)
            show_hidden: Include hidden files/directories

        Returns:
            Dict with files, directories, and path
        """
        try:
            if not os.path.isabs(path):
                path = os.path.join(workspace_root, path)

            dir_path = _validate_path(path, workspace_root)

            if not dir_path.exists():
                return {"error": f"Directory not found: {path}"}

            if not dir_path.is_dir():
                return {"error": f"Not a directory: {path}"}

            entries = sorted(dir_path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))

            files = []
            directories = []

            for entry in entries:
                if not show_hidden and entry.name.startswith("."):
                    continue

                if entry.is_dir():
                    directories.append(entry.name + "/")
                else:
                    files.append(entry.name)

            return {
                "path": str(dir_path),
                "directories": directories,
                "files": files,
                "total": len(directories) + len(files),
            }
        except Exception as e:
            return {"error": str(e)}

    @tool
    def find_files(pattern: str, path: str = ".", max_depth: Optional[int] = None) -> dict:
        """
        Find files matching a glob pattern.

        Args:
            pattern: Glob pattern (e.g., "**/*.py", "*.ts", "src/**/*test*.js")
            path: Starting directory (absolute or relative to workspace)
            max_depth: Maximum directory depth to search

        Returns:
            Dict with matching file paths
        """
        try:
            if not os.path.isabs(path):
                path = os.path.join(workspace_root, path)

            dir_path = _validate_path(path, workspace_root)

            if not dir_path.exists():
                return {"error": f"Directory not found: {path}"}

            matches = []

            for match in dir_path.glob(pattern):
                if match.is_file():
                    rel_path = match.relative_to(dir_path)

                    if max_depth is not None and len(rel_path.parts) > max_depth:
                        continue

                    matches.append(str(rel_path))

                    if len(matches) >= max_results:
                        break

            return {
                "pattern": pattern,
                "base_path": str(dir_path),
                "matches": matches,
                "count": len(matches),
                "truncated": len(matches) >= max_results,
            }
        except Exception as e:
            return {"error": str(e)}

    @tool
    def grep(
        pattern: str,
        path: str = ".",
        file_pattern: str = "*",
        case_sensitive: bool = True,
        context_lines: int = 0,
    ) -> dict:
        """
        Search for text patterns in files.

        Args:
            pattern: Regex pattern to search for
            path: Directory to search (absolute or relative to workspace)
            file_pattern: Glob pattern for files to search (e.g., "*.py")
            case_sensitive: Case-sensitive search
            context_lines: Number of context lines before/after match

        Returns:
            Dict with matches grouped by file
        """
        try:
            if not os.path.isabs(path):
                path = os.path.join(workspace_root, path)

            dir_path = _validate_path(path, workspace_root)

            if not dir_path.exists():
                return {"error": f"Directory not found: {path}"}

            flags = 0 if case_sensitive else re.IGNORECASE
            regex = re.compile(pattern, flags)

            results = []
            total_matches = 0

            glob_pattern = f"**/{file_pattern}" if not file_pattern.startswith("**") else file_pattern

            for file_path in dir_path.glob(glob_pattern):
                if not file_path.is_file():
                    continue

                if _is_binary_file(file_path):
                    continue

                try:
                    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                        lines = f.readlines()
                except Exception:
                    continue

                file_matches = []

                for i, line in enumerate(lines):
                    if regex.search(line):
                        match_info = {
                            "line_number": i + 1,
                            "content": line.rstrip(),
                        }

                        if context_lines > 0:
                            start = max(0, i - context_lines)
                            end = min(len(lines), i + context_lines + 1)
                            match_info["context"] = [
                                f"{j + 1}: {lines[j].rstrip()}"
                                for j in range(start, end)
                            ]

                        file_matches.append(match_info)
                        total_matches += 1

                        if total_matches >= max_results:
                            break

                if file_matches:
                    results.append({
                        "file": str(file_path.relative_to(dir_path)),
                        "matches": file_matches,
                    })

                if total_matches >= max_results:
                    break

            return {
                "pattern": pattern,
                "base_path": str(dir_path),
                "results": results,
                "total_matches": total_matches,
                "truncated": total_matches >= max_results,
            }
        except re.error as e:
            return {"error": f"Invalid regex pattern: {e}"}
        except Exception as e:
            return {"error": str(e)}

    @tool
    def get_file_info(path: str) -> dict:
        """
        Get metadata about a file or directory.

        Args:
            path: Path to file or directory

        Returns:
            Dict with file metadata (size, type, permissions, etc.)
        """
        try:
            if not os.path.isabs(path):
                path = os.path.join(workspace_root, path)

            file_path = _validate_path(path, workspace_root)

            if not file_path.exists():
                return {"error": f"Path not found: {path}"}

            stat = file_path.stat()

            return {
                "path": str(file_path),
                "name": file_path.name,
                "type": "directory" if file_path.is_dir() else "file",
                "size_bytes": stat.st_size,
                "is_binary": _is_binary_file(file_path) if file_path.is_file() else None,
                "extension": file_path.suffix if file_path.is_file() else None,
            }
        except Exception as e:
            return {"error": str(e)}

    return [
        read_file,
        write_file,
        edit_file,
        list_directory,
        find_files,
        grep,
        get_file_info,
    ]
