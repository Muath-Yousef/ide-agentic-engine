"""
Sentry error tracking — call ``setup_sentry()`` once at process start.
Free tier: 5 000 errors / month.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


def setup_sentry() -> None:
    """
    Initialise Sentry SDK.

    Requires ``SENTRY_DSN`` in environment.  No-ops silently if not set,
    so development environments need no configuration.
    """
    dsn = os.environ.get("SENTRY_DSN", "")
    if not dsn:
        logger.debug("SENTRY_DSN not set — Sentry disabled")
        return

    try:
        import sentry_sdk
        from sentry_sdk.integrations.logging import LoggingIntegration
    except ImportError:
        logger.warning("sentry-sdk not installed — error tracking disabled")
        return

    version = os.environ.get("ENGINE_VERSION", "2.0.0")
    environment = os.environ.get("ENVIRONMENT", "development")

    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        release=f"ide-agentic-engine@{version}",
        traces_sample_rate=0.1,   # 10 % of transactions traced
        profiles_sample_rate=0.1,
        integrations=[
            LoggingIntegration(
                level=logging.INFO,
                event_level=logging.ERROR,
            )
        ],
        before_send=_scrub_secrets,
    )
    logger.info("Sentry initialised: env=%s release=%s@%s", environment, "ide-agentic-engine", version)


def _scrub_secrets(event: dict, hint: dict) -> dict:
    """Strip any accidental API key leakage before sending to Sentry."""
    import re
    _SECRET_RE = re.compile(
        r"(api[_-]?key|password|secret|token|dsn)\s*[=:]\s*\S+",
        re.IGNORECASE,
    )
    # Walk string values in the event dict and redact matches
    if "extra" in event:
        for k, v in event["extra"].items():
            if isinstance(v, str):
                event["extra"][k] = _SECRET_RE.sub(r"\1=[REDACTED]", v)
    return event
