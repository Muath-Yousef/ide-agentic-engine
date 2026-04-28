"""
Code Skeleton Tool Server — wraps engine.token_optimizer.get_code_skeleton.

Provides a clean MCP tool interface for the AST-based skeleton extractor.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_WORKSPACE = Path(os.environ.get("WORKSPACE_ROOT", ".")).resolve()


def get_code_skeleton(path: str, include_private: bool = False) -> str:
    """
    Extract class and function signatures from a Python file.

    Returns only signatures (no implementations), saving ~95 % of tokens
    versus reading the full source.

    Args:
        path: Relative path from workspace root.
        include_private: If False (default), omit methods starting with ``__``.

    Returns:
        String skeleton with class/function signatures and first-line docstrings.
    """
    from engine.token_optimizer import get_code_skeleton as _skeleton

    full_path = (_WORKSPACE / path).resolve()

    # Safety: ensure path stays within workspace
    try:
        full_path.relative_to(_WORKSPACE)
    except ValueError:
        raise PermissionError(f"Path traversal blocked: {path}")

    raw_skeleton = _skeleton(str(full_path))

    if not include_private:
        filtered = _filter_private_members(raw_skeleton)
        return filtered

    return raw_skeleton


def get_directory_skeleton(directory: str = ".") -> dict[str, Any]:
    """
    Return skeletons for all Python files in *directory*.

    Useful for giving the agent a project-wide map in a single batch call.

    Args:
        directory: Relative path from workspace root (default: root).

    Returns:
        Dict mapping relative_path → skeleton string.
    """
    dir_path = (_WORKSPACE / directory).resolve()
    try:
        dir_path.relative_to(_WORKSPACE)
    except ValueError:
        raise PermissionError(f"Path traversal blocked: {directory}")

    skeletons: dict[str, str] = {}
    for py_file in sorted(dir_path.rglob("*.py")):
        # Skip common non-source directories
        parts = py_file.parts
        if any(d in parts for d in ("venv", "__pycache__", ".git", "node_modules")):
            continue
        rel = str(py_file.relative_to(_WORKSPACE))
        skeletons[rel] = get_code_skeleton(rel)

    total_chars = sum(len(v) for v in skeletons.values())
    logger.info(
        "Directory skeleton: %d files, ~%d chars (~%d tokens)",
        len(skeletons),
        total_chars,
        total_chars // 4,
    )
    return {
        "files": skeletons,
        "file_count": len(skeletons),
        "estimated_tokens": total_chars // 4,
    }


def _filter_private_members(skeleton: str) -> str:
    """Remove lines containing dunder methods (except __init__ and __repr__)."""
    keep_dunders = {"__init__", "__repr__", "__str__", "__enter__", "__exit__"}
    lines = []
    for line in skeleton.splitlines():
        stripped = line.strip()
        # Check if it's a dunder method definition
        if stripped.startswith("def __") or stripped.startswith("async def __"):
            method_name = stripped.split("(")[0].split()[-1]
            if method_name not in keep_dunders:
                continue
        lines.append(line)
    return "\n".join(lines)
