# SOCROOT: Advanced Agentic SOAR Engine 🛡️🤖

**SOCROOT** is a production-grade, autonomous security orchestration and remediation engine. It transforms static security alerts into active defense maneuvers by leveraging advanced LLM agents to plan, validate, and execute security fixes. 

Recently, the project has evolved into a **Unified Monorepo**, seamlessly bridging the development layer (IDE Agentic Engine) and the production layer (SOC Core Platform).

## 🚀 The Monorepo Architecture

The repository is structured as a `uv` workspace to ensure dependency isolation and rapid execution:

- **`packages/ide-engine/`**: The brain of the operation. Contains the `AgentOrchestrator`, LLM provider routing, and the FastAPI Webhook Listener.
- **`packages/soc-core/`**: The production platform. Manages clients, evidence chains, and audit-grade data storage.
- **`packages/shared_mcps/`** *(Phase 1)*: The Bridge Layer. Provides standardized Model Context Protocol (MCP) servers (`State`, `Evidence`, `Development`) allowing agents to interact with production SOC features safely.
- **`packages/shared_skills/`** *(Phase 2)*: The Intelligence Layer. A library of expert markdown templates (`soc_triage`, `incident_response`, `iac_management`) that are dynamically injected into agents, turning them into domain experts.

## 🔥 Key Features

### 1. The "Master Hook" (Self-Healing Operations)
The system is fully autonomous. When Wazuh (or any SIEM) detects a critical vulnerability, it sends a webhook to the `ide-engine`. The **Master Hook Dispatcher** intercepts this, logs it to the `EvidenceStore`, and immediately triggers the `AgentOrchestrator` to begin triage and remediation without human intervention.

### 2. Autonomous Auto-Remediation
- **Intelligent Planning**: Uses multi-provider LLMs (Gemini, OpenAI, DeepSeek, Groq) to generate surgical remediation plans.
- **Shared Skills**: Agents read from `shared_skills` to apply best-practice response protocols dynamically.

### 3. Human-in-the-Loop (HITL)
- **Critical Action Guards**: Automatically pauses execution and requests human approval for sensitive operations (e.g., executing system commands, isolating networks).
- **Audit-Grade Evidence**: Every step the agent takes, including its thought process and human approvals, is hashed and stored in the tamper-evident `EvidenceStore`.

## 🛠️ Getting Started

### Prerequisites
- Python 3.10+
- `uv` for lightning-fast monorepo dependency management

### Installation
```bash
git clone <repo-url>
cd SOCROOT
# Sync the entire workspace environment
uv sync
```

### Starting the Engine
1. **Launch the Master Hook (Webhook Listener)**:
   ```bash
   uv run python packages/ide-engine/engine/webhook_listener.py
   ```
2. **Trigger Auto-Remediation via Webhook**:
   Send a JSON payload simulating a Wazuh alert to `http://0.0.0.0:8000/webhook/wazuh`. The engine will automatically catch it, start an evidence chain, and deploy an agent.

## 🧪 Testing the Integration
A master test script is provided to verify the workspace, skill loading, and MCP connections:
```bash
uv run python packages/test_system_integration.py
```

---
*Built with ❤️ by the SOCROOT Engineering Team.*
