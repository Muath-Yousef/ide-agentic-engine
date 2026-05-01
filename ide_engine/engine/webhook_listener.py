from dotenv import load_dotenv
# Load environment variables from .env BEFORE any other imports
load_dotenv()

import logging
import uuid
import asyncio
from typing import Any, Dict

from fastapi import BackgroundTasks, FastAPI, Request

from agents.remediation_agent import run_auto_remediation
from socroot.evidence_store import EvidenceStore

logger = logging.getLogger(__name__)

app = FastAPI(title="SOCROOT Webhook Listener")
store = EvidenceStore()


async def dispatch_remediation_agent(finding: dict):
    """
    The 'Master Hook' Dispatcher.
    Triggers the autonomous AgentOrchestrator and handles SOC evidence tracking.
    """
    finding_id = finding.get("finding_id", "UNKNOWN")
    logger.info(f"🚀 Dispatching Auto-Remediation Agent for {finding_id}...")
    
    # 1. Log incident start (Evidence tracking)
    client_id = finding.get("client", "UNKNOWN_CLIENT")
    store.add_record(
        client_id=client_id,
        finding=finding,
        metadata={"status": "Triage Started", "timestamp": "now"}
    )
    
    # 2. Trigger the agent
    try:
        session_id, state = await run_auto_remediation(finding)
        logger.info(f"✅ Remediation Session {session_id} completed or paused for HITL. State: {state.get('pending_approval')}")
        
        # 3. Log incident update
        store.add_record(
            client_id=client_id,
            finding=finding,
            metadata={"status": "Triage Paused/Completed", "session_id": session_id}
        )
    except Exception as e:
        logger.error(f"❌ Failed to execute remediation agent: {e}")


@app.get("/health")
async def health_check():
    return {"status": "nominal"}


@app.post("/webhook/wazuh")
async def wazuh_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Handle incoming alerts from Wazuh SIEM.
    Expects Wazuh Alert JSON format.
    """
    data = await request.json()
    alert_id = data.get("id")
    rule = data.get("rule", {})
    level = rule.get("level", 0)
    description = rule.get("description", "Unknown Alert")

    logger.info(f"Received Wazuh Alert: {alert_id} (Level {level}) - {description}")

    # We only auto-remediate high severity alerts (e.g. level >= 10)
    if level >= 7:
        # Map Wazuh alert to a finding structure
        finding = {
            "finding_id": f"WAZUH-{alert_id}",
            "title": description,
            "severity": "high" if level >= 10 else "medium",
            "remediation_summary": f"Alert triggered by Wazuh rule {rule.get('id')}. Full description: {description}",
            "client": "DefaultClient",  # In production, map this via IP/AgentID
        }

        # Run remediation via Master Hook dispatcher
        background_tasks.add_task(dispatch_remediation_agent, finding)
        return {"status": "accepted", "remediation_triggered": True, "alert_id": alert_id}

    return {"status": "ignored", "reason": "severity_too_low", "level": level}


@app.post("/webhook/generic")
async def generic_webhook(data: Dict[str, Any], background_tasks: BackgroundTasks):
    """
    Generic webhook for custom security finding triggers.
    """
    logger.info(f"Received Generic Webhook Finding: {data.get('title')}")

    # Trigger remediation via Master Hook dispatcher
    background_tasks.add_task(dispatch_remediation_agent, data)

    return {"status": "accepted", "remediation_triggered": True}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
