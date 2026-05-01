"""
Evidence Store — append-only, tamper-evident record chain.

Each record contains the SHA-256 of its content + the hash of the
previous record, forming a verifiable chain.  Records are stored as
JSON Lines in ``knowledge/evidence/{client_id}.jsonl``.

Rules enforced:
  - Records are NEVER modified after creation.
  - Deletion is prohibited (only append allowed).
  - ``verify_chain()`` validates the entire hash chain.
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).parent.parent
_EVIDENCE_ROOT = _PROJECT_ROOT / "knowledge/evidence"
_EVIDENCE_ROOT.mkdir(parents=True, exist_ok=True)


class EvidenceStore:
    """Append-only evidence record manager with hash-chaining."""

    def __init__(self, base_dir: Path | None = None) -> None:
        self._base = base_dir or _EVIDENCE_ROOT

    # ------------------------------------------------------------------
    # Write — append only
    # ------------------------------------------------------------------

    def add_record(
        self,
        client_id: str,
        finding: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Append a new evidence record for *client_id*.

        Returns the complete record dict (including hashes) for state storage.
        """
        chain_file = self._chain_file(client_id)
        previous_hash = self._last_hash(chain_file)

        record: dict[str, Any] = {
            "record_id": str(uuid.uuid4()),
            "client_id": client_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "finding": finding,
            "metadata": metadata or {},
            "previous_hash": previous_hash,
        }

        # Hash the content (everything except the hash field itself)
        content_hash = self._hash_record(record)
        record["sha256_hash"] = content_hash

        # Append to JSONL file
        with open(chain_file, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

        logger.debug(
            "Evidence record added: client=%s id=%s hash=...%s",
            client_id,
            record["record_id"],
            content_hash[-8:],
        )
        return record

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get_records(self, client_id: str) -> list[dict[str, Any]]:
        """Return all evidence records for *client_id* in chronological order."""
        chain_file = self._chain_file(client_id)
        if not chain_file.exists():
            return []
        records = []
        with open(chain_file, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records

    # ------------------------------------------------------------------
    # Verification
    # ------------------------------------------------------------------

    def verify_chain(self, client_id: str) -> tuple[bool, str]:
        """
        Verify the integrity of the evidence chain.

        Returns:
            (True, "OK") if valid.
            (False, error_message) if tampered.
        """
        records = self.get_records(client_id)
        if not records:
            return True, "OK (empty chain)"

        prev_hash: str | None = None
        for i, record in enumerate(records):
            stored_hash = record.get("sha256_hash", "")
            expected_previous = record.get("previous_hash")

            # Check previous-hash linkage
            if expected_previous != prev_hash:
                return (
                    False,
                    f"Chain broken at record {i} (id={record.get('record_id')}): "
                    f"expected previous_hash={prev_hash!r}, got {expected_previous!r}",
                )

            # Re-compute content hash
            record_copy = {k: v for k, v in record.items() if k != "sha256_hash"}
            recomputed = self._hash_record(record_copy)
            if recomputed != stored_hash:
                return (
                    False,
                    f"Content hash mismatch at record {i} (id={record.get('record_id')}): "
                    f"stored={stored_hash!r}, computed={recomputed!r}",
                )

            prev_hash = stored_hash

        return True, f"OK ({len(records)} records verified)"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _chain_file(self, client_id: str) -> Path:
        safe_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in client_id)
        return self._base / f"{safe_id}.jsonl"

    @staticmethod
    def _last_hash(chain_file: Path) -> str | None:
        """Read the sha256_hash of the last record in the file."""
        if not chain_file.exists():
            return None
        last_line = ""
        with open(chain_file, "r", encoding="utf-8") as fh:
            for line in fh:
                stripped = line.strip()
                if stripped:
                    last_line = stripped
        if not last_line:
            return None
        try:
            return json.loads(last_line).get("sha256_hash")
        except json.JSONDecodeError:
            return None

    @staticmethod
    def _hash_record(record: dict[str, Any]) -> str:
        """SHA-256 of the canonically serialised record (sorted keys)."""
        canonical = json.dumps(record, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Module-level helper for pre-commit hook
# ---------------------------------------------------------------------------


def verify_all_chains() -> None:
    """
    Verify all evidence chains in the store.

    Called by the pre-commit hook to catch tampering before any commit.
    Raises SystemExit(1) on failure.
    """
    import sys

    store = EvidenceStore()
    failed = False
    for chain_file in _EVIDENCE_ROOT.glob("*.jsonl"):
        client_id = chain_file.stem
        ok, msg = store.verify_chain(client_id)
        status = "✓" if ok else "✗"
        print(f"  {status} {client_id}: {msg}")
        if not ok:
            failed = True

    if failed:
        print("\n❌ Evidence chain integrity check FAILED", file=sys.stderr)
        sys.exit(1)
    print("✅ All evidence chains OK")
