# SOCROOT: Advanced Agentic SOAR Engine 🛡️🤖

**SOCROOT** is a production-grade, autonomous security orchestration and remediation engine. It transforms static security alerts into active defense maneuvers by leveraging advanced LLM agents to plan, validate, and execute security fixes.

## 🚀 Core Capabilities

### 1. Autonomous Auto-Remediation (Axis 1)
- **Intelligent Planning**: Uses multi-provider LLMs (Gemini, OpenAI, DeepSeek, Groq) to generate surgical remediation plans.
- **Provider Resilience**: Implements a robust **Key Rotation Pool** with Round-Robin scheduling to bypass rate limits (429 errors).
- **Safety First**: Native role mapping and schema enforcement ensure structured, predictable agent behavior.

### 2. Human-in-the-Loop (Axis 2)
- **Critical Action Guards**: Automatically pauses execution and requests human approval for sensitive operations (`git_push`, `run_command`, etc.).
- **Persistent Sessions**: State is managed via **Redis**, allowing sessions to survive restarts and ensuring long-running remediation tasks are never lost.

### 3. Real-World Tool Integration (Axis 3)
- **Nuclei Adapter**: Automated vulnerability scanning with real-time JSON result parsing.
- **Wazuh Adapter**: Deep integration with SIEM for alert retrieval, agent inventory, and endpoint interrogation.
- **Secure Execution**: All tools run in isolated sub-processes with strict error handling and output pruning.

### 4. Event-Driven Monitoring (Axis 4)
- **Webhook Listener**: A high-performance FastAPI service that triggers remediation workflows the moment an alert is received from external systems (SIEM/EDR).

## 🛠️ Getting Started

### Prerequisites
- Python 3.10+
- Docker & Docker Compose (for Redis)
- `uv` for lightning-fast dependency management

### Installation
```bash
git clone <repo-url>
cd SOCROOT
uv pip install -e .
```

### Starting the Engine
1. **Start Infrastructure**:
   ```bash
   docker-compose -f deployment/docker-compose.yml up -d redis
   ```
2. **Launch Monitoring Listener**:
   ```bash
   ide-agent monitor --port 8000
   ```
3. **Trigger Manual Remediation**:
   ```bash
   ide-agent remediate --finding-id CVE-2024-XXXX --client ExampleCorp
   ```

## 📂 Architecture
- `core/`: State management, Orchestrator, and KeyPool.
- `agents/`: Specialized agent logic (Remediation, Triage).
- `engine/providers/`: Resilient LLM adapters (Gemini, OpenAI, Groq, DeepSeek).
- `socroot/`: Security adapters and Evidence Store.

---
*Built with ❤️ by the SOCROOT Engineering Team.*
