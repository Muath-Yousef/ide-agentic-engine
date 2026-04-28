import json
import logging
import asyncio
from fastmcp import FastMCP
from typing import Dict, Any, List

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("socroot-state-server")

# Initialize FastMCP Server
mcp = FastMCP("socroot-state-server")

# In a real scenario, this would connect to Redis or PostgreSQL
# For now, we simulate a state store
_state_store = {
    "clients": {
        "client_001": {
            "name": "Acme Corp",
            "compliance_score": 85,
            "active_scans": 2,
            "open_incidents": 1
        }
    },
    "tasks": [
        {"id": "TASK-1", "priority": "high", "description": "Fix critical SQLi vulnerability", "status": "pending"},
        {"id": "TASK-2", "priority": "medium", "description": "Update TLS configurations", "status": "pending"}
    ],
    "deployments": [],
    "system_health": {
        "status": "operational",
        "uptime_hours": 340,
        "active_agents": 12
    }
}

@mcp.tool()
async def get_client_state(client_id: str) -> Dict[str, Any]:
    """
    Get the current state of a client (scans, evidence, compliance score).
    """
    logger.info(f"Fetching state for client: {client_id}")
    client_data = _state_store["clients"].get(client_id)
    if not client_data:
        return {"error": f"Client {client_id} not found."}
    return client_data

@mcp.tool()
async def get_pending_tasks(priority: str = "high") -> List[Dict[str, Any]]:
    """
    Get tasks awaiting development (new features, bug fixes) filtered by priority.
    """
    logger.info(f"Fetching pending tasks with priority: {priority}")
    tasks = [t for t in _state_store["tasks"] if t["priority"].lower() == priority.lower() and t["status"] == "pending"]
    return tasks

@mcp.tool()
async def update_deployment_status(phase: str, status: str, details: str) -> str:
    """
    Update status after code deployment.
    """
    logger.info(f"Updating deployment status - Phase: {phase}, Status: {status}")
    deployment_record = {
        "phase": phase,
        "status": status,
        "details": details
    }
    _state_store["deployments"].append(deployment_record)
    return "Deployment status updated successfully."

@mcp.tool()
async def get_system_health() -> Dict[str, Any]:
    """
    Overall platform health (uptime, errors, performance).
    """
    logger.info("Fetching system health metrics")
    return _state_store["system_health"]

if __name__ == "__main__":
    logger.info("Starting SOC Root State Server...")
    mcp.run(transport="stdio")
