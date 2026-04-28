"""Tests for socroot/evidence_store.py."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from socroot.evidence_store import EvidenceStore


@pytest.fixture()
def store(tmp_path: Path) -> EvidenceStore:
    return EvidenceStore(base_dir=tmp_path)


def test_add_record_creates_file(store: EvidenceStore, tmp_path: Path) -> None:
    store.add_record("client1", {"title": "test finding", "severity": "high"})
    chain_files = list(tmp_path.glob("*.jsonl"))
    assert len(chain_files) == 1


def test_added_record_has_required_fields(store: EvidenceStore) -> None:
    record = store.add_record("c1", {"severity": "medium"})
    assert "record_id" in record
    assert "timestamp" in record
    assert "sha256_hash" in record
    assert record["client_id"] == "c1"


def test_chain_links_consecutive_records(store: EvidenceStore) -> None:
    r1 = store.add_record("c1", {"n": 1})
    r2 = store.add_record("c1", {"n": 2})
    assert r2["previous_hash"] == r1["sha256_hash"]


def test_verify_chain_passes_on_valid_chain(store: EvidenceStore) -> None:
    for i in range(5):
        store.add_record("c1", {"index": i})
    ok, msg = store.verify_chain("c1")
    assert ok is True
    assert "5 records" in msg


def test_verify_chain_empty(store: EvidenceStore) -> None:
    ok, msg = store.verify_chain("nonexistent")
    assert ok is True
    assert "empty" in msg


def test_verify_chain_detects_hash_tampering(
    store: EvidenceStore, tmp_path: Path
) -> None:
    store.add_record("victim", {"data": "original"})
    chain_file = tmp_path / "victim.jsonl"
    raw = chain_file.read_text()
    record = json.loads(raw.strip())
    record["finding"]["data"] = "tampered"  # modify content
    chain_file.write_text(json.dumps(record) + "\n")

    ok, msg = store.verify_chain("victim")
    assert ok is False
    assert "mismatch" in msg.lower() or "hash" in msg.lower()


def test_first_record_has_null_previous_hash(store: EvidenceStore) -> None:
    r = store.add_record("c1", {"x": 1})
    assert r["previous_hash"] is None


def test_get_records_returns_in_order(store: EvidenceStore) -> None:
    for i in range(10):
        store.add_record("ordered", {"seq": i})
    records = store.get_records("ordered")
    assert len(records) == 10
    for i, rec in enumerate(records):
        assert rec["finding"]["seq"] == i


def test_get_records_empty_for_unknown_client(store: EvidenceStore) -> None:
    assert store.get_records("nobody") == []
