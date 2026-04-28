# Skill: Evidence Chain Verification Expert

## When to Use
Tasks involving hash chain integrity, WORM storage validation

## Core Knowledge
- SHA-256 computation
- Append-only JSONL format
- Chain verification: prev_hash matching

## Test Commands
python3 -c "from soc.evidence_store import verify_chain; print(verify_chain())"
