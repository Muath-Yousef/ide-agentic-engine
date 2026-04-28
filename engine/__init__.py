"""ide-agentic-engine v2.0 — CLI Agentic Engine for IDE AI workflows."""

from __future__ import annotations

import importlib
import os
import sys

__version__ = "2.0.0"
__author__ = "ide-agentic-engine contributors"

_REQUIRED_ENV_VARS: list[str] = [
    "ANTHROPIC_API_KEY",
    "REDIS_URL",
]

_REQUIRED_PACKAGES: list[str] = [
    "anthropic",
    "instructor",
    "langgraph",
    "pydantic",
    "redis",
    "opentelemetry",
]


def self_check() -> bool:
    """
    Validate runtime environment before startup.
    Returns True if all checks pass, raises SystemExit otherwise.
    """
    errors: list[str] = []

    for var in _REQUIRED_ENV_VARS:
        if not os.environ.get(var):
            errors.append(f"  ✗ Missing env var: {var}")

    for pkg in _REQUIRED_PACKAGES:
        try:
            importlib.import_module(pkg)
        except ImportError:
            errors.append(f"  ✗ Missing package: {pkg}")

    if errors:
        print("❌ Environment check failed:\n" + "\n".join(errors), file=sys.stderr)
        print("\nRun: just setup", file=sys.stderr)
        raise SystemExit(1)

    print(f"✅ ide-agentic-engine v{__version__} — environment OK")
    return True
