#!/usr/bin/env python3
"""
Seed Script: Inject a realistic security finding into the EvidenceStore
for the live Auto-Remediation drill.
"""
import os
import sys

sys.path.insert(0, "/media/kyrie/SOCROOT")
os.chdir("/media/kyrie/SOCROOT")

from socroot.evidence_store import EvidenceStore

store = EvidenceStore()

finding = {
    "finding_id": "NUC-2024-XSS-001",
    "title": "Missing Security Headers & Reflected XSS",
    "severity": "high",
    "cvss_score": 7.5,
    "nca_control_ids": ["ECC-2-2-1", "ECC-2-4-1"],
    "remediation_summary": (
        "The file reports/asasedu_webapp_config.py has multiple critical issues: "
        "(1) Reflected XSS in /user/<username> route - no input sanitization. "
        "(2) DEBUG=True in production. "
        "(3) Hardcoded SECRET_KEY. "
        "Fix: Add input escaping via markupsafe.escape(), set DEBUG=False, "
        "load SECRET_KEY from environment variable os.environ.get('SECRET_KEY')."
    ),
    "remediation_priority": 1,
    "attack_vector": "Network",
}

record = store.add_record(
    client_id="AsasEdu",
    finding=finding,
    metadata={
        "nca_control_ids": finding["nca_control_ids"],
        "compliance_score": 45.0,
        "scan_tool": "nuclei",
        "target": "asas4edu.net",
    },
)

print(f"✅ Finding seeded successfully!")
print(f"   finding_id : {finding['finding_id']}")
print(f"   record_id  : {record['record_id']}")
print(f"   client_id  : AsasEdu")
print()
print(f"Run this command to start remediation:")
print(f"  just remediate-finding --client AsasEdu --finding-id {finding['finding_id']}")
print(f"  # OR directly:")
print(
    f"  PYTHONPATH=. uv run ide-agent remediate --finding-id {finding['finding_id']} --client AsasEdu"
)
