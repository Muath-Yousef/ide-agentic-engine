import asyncio
import logging
from fastapi.testclient import TestClient

# Mock imports by adding path
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "ide-engine"))

from engine.webhook_listener import app

client = TestClient(app)

def test_master_hook():
    print("=== Testing SOCROOT Master Hook (Phase 3) ===")
    
    mock_wazuh_payload = {
        "id": "1618301821.123456",
        "rule": {
            "level": 12,
            "description": "Critical SSH Brute Force Detected",
            "id": "5710"
        },
        "agent": {
            "name": "srv-prod-01",
            "ip": "10.0.0.50"
        }
    }
    
    print("1. Sending Mock Wazuh Alert (Severity: Critical)...")
    response = client.post("/webhook/wazuh", json=mock_wazuh_payload)
    
    print(f"2. Response Status Code: {response.status_code}")
    print(f"3. Response Payload: {response.json()}")
    
    if response.status_code == 200 and response.json().get("remediation_triggered"):
        print("[SUCCESS] Master Hook successfully intercepted the alert and dispatched the Remediation Agent!")
    else:
        print("[FAILED] Master Hook did not trigger the expected response.")

if __name__ == "__main__":
    # Configure logging to see the dispatcher logs
    logging.basicConfig(level=logging.INFO)
    test_master_hook()
