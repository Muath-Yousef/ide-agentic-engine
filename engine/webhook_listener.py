import logging
import uuid
from typing import Any, Dict

from fastapi import BackgroundTasks, FastAPI, Request

from agents.remediation_agent import run_auto_remediation
from socroot.evidence_store import EvidenceStore

logger = logging.getLogger(__name__)

app = FastAPI(title="SOCROOT Webhook Listener")
store = EvidenceStore()


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

        # Run remediation in the background
        background_tasks.add_task(run_auto_remediation, finding)
        return {"status": "accepted", "remediation_triggered": True, "alert_id": alert_id}

    return {"status": "ignored", "reason": "severity_too_low", "level": level}


@app.post("/webhook/generic")
async def generic_webhook(data: Dict[str, Any], background_tasks: BackgroundTasks):
    """
    Generic webhook for custom security finding triggers.
    """
    logger.info(f"Received Generic Webhook Finding: {data.get('title')}")

    # Trigger remediation immediately
    background_tasks.add_task(run_auto_remediation, data)

    return {"status": "accepted", "remediation_triggered": True}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
