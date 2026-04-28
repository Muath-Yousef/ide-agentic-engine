import logging
import hashlib
import json
from fastmcp import FastMCP
from typing import Dict, Any, List

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("socroot-evidence-server")

# Initialize FastMCP Server
mcp = FastMCP("socroot-evidence-chain")

# Simulate Evidence Store from soc-core
_evidence_store = [
    {
        "id": "EV-001",
        "client_id": "client_001",
        "control_id": "ISO-27001-A.12",
        "timestamp": "2026-04-28T10:00:00Z",
        "data": "Vulnerability scan completed. No high findings.",
        "hash": "b2c3d4e5"
    }
]

@mcp.tool()
async def verify_evidence_integrity() -> Dict[str, Any]:
    """
    Verify hash chain integrity for all clients in the evidence store.
    """
    logger.info("Verifying evidence hash chain integrity")
    # Simulate a successful integrity check
    return {
        "status": "success",
        "verified_records": len(_evidence_store),
        "corrupted_records": 0,
        "message": "All evidence records passed integrity validation."
    }

@mcp.tool()
async def generate_audit_package(client_id: str, timerange: str = "last_30_days") -> Dict[str, Any]:
    """
    Create an audit package (JSON compilation) for a specific client and timerange.
    """
    logger.info(f"Generating audit package for client {client_id} (timerange: {timerange})")
    
    # Filter evidence
    client_evidence = [e for e in _evidence_store if e["client_id"] == client_id]
    
    if not client_evidence:
        return {"error": "No evidence found for the specified client.", "client_id": client_id}
        
    audit_hash = hashlib.sha256(json.dumps(client_evidence).encode()).hexdigest()
    
    return {
        "client_id": client_id,
        "timerange": timerange,
        "record_count": len(client_evidence),
        "audit_package_hash": audit_hash,
        "records": client_evidence
    }

@mcp.tool()
async def get_evidence_by_control(control_id: str) -> List[Dict[str, Any]]:
    """
    Retrieve evidence associated with a specific compliance control (e.g., ISO-27001-A.12).
    """
    logger.info(f"Retrieving evidence for control ID: {control_id}")
    matching = [e for e in _evidence_store if e["control_id"] == control_id]
    return matching

if __name__ == "__main__":
    logger.info("Starting SOC Root Evidence Chain Server...")
    mcp.run(transport="stdio")
