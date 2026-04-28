"""
Filesystem Tool Server — production-grade file operations.

All paths are validated against a configurable whitelist to prevent
directory traversal attacks.  Write operations create parent directories
automatically.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Configurable root — tool cannot read/write outside this directory tree
_ALLOWED_ROOT = Path(os.environ.get("WORKSPACE_ROOT", ".")).resolve()


def _safe_path(path: str) -> Path:
    """
    Resolve *path* and assert it stays within _ALLOWED_ROOT.

    Raises:
        PermissionError: If path escapes the allowed root.
    """
    resolved = (_ALLOWED_ROOT / path).resolve()
    try:
        resolved.relative_to(_ALLOWED_ROOT)
    except ValueError:
        raise PermissionError(
            f"Path traversal blocked: '{path}' resolves outside workspace root"
        )
    return resolved


def read_file(path: str, encoding: str = "utf-8") -> str:
    """
    Read and return the full content of *path*.

    For large files, consider using ``get_code_skeleton`` instead to save tokens.

    Args:
        path: Relative path from workspace root.
        encoding: File encoding (default utf-8).

    Returns:
        File content as a string.
    """
    safe = _safe_path(path)
    if not safe.exists():
        raise FileNotFoundError(f"File not found: {path}")
    content = safe.read_text(encoding=encoding)
    logger.debug("read_file: %s (%d chars)", path, len(content))
    return content


def write_file(path: str, content: str, encoding: str = "utf-8") -> dict[str, Any]:
    """
    Write *content* to *path*, creating parent directories if needed.

    Args:
        path: Relative path from workspace root.
        content: String content to write.
        encoding: File encoding (default utf-8).

    Returns:
        Dict with path, bytes_written, created (bool).
    """
    safe = _safe_path(path)
    existed = safe.exists()
    safe.parent.mkdir(parents=True, exist_ok=True)
    safe.write_text(content, encoding=encoding)
    bytes_written = len(content.encode(encoding))
    logger.info("write_file: %s (%d bytes, created=%s)", path, bytes_written, not existed)
    return {
        "path": str(safe),
        "bytes_written": bytes_written,
        "created": not existed,
    }


def apply_diff(path: str, old_text: str, new_text: str) -> dict[str, Any]:
    """
    Apply a search-and-replace patch to *path*.

    This is the preferred way to edit files — the agent sends only
    the changed lines, saving ~80 % of output tokens vs full rewrite.

    Args:
        path: Relative path from workspace root.
        old_text: Exact text to find and replace.
        new_text: Replacement text.

    Returns:
        Dict with success (bool) and message.
    """
    from engine.token_optimizer import apply_diff_patch

    safe = _safe_path(path)
    success = apply_diff_patch(str(safe), old_text, new_text)
    return {
        "success": success,
        "path": path,
        "message": "Patch applied." if success else "old_text not found — no changes made.",
    }


def list_directory(path: str = ".") -> dict[str, Any]:
    """
    List files and directories under *path*.

    Args:
        path: Relative path from workspace root (default: root).

    Returns:
        Dict with dirs (list) and files (list).
    """
    safe = _safe_path(path)
    if not safe.is_dir():
        raise NotADirectoryError(f"Not a directory: {path}")

    dirs = sorted(str(p.relative_to(safe)) for p in safe.iterdir() if p.is_dir())
    files = sorted(str(p.relative_to(safe)) for p in safe.iterdir() if p.is_file())
    return {"path": path, "dirs": dirs, "files": files}
