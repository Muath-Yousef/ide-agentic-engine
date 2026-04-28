# Project Handoff: IDE Agentic Engine

This document outlines the current state and robust foundation of the **IDE Agentic Engine** project. 

## 📌 Project Overview
The **IDE Agentic Engine** is designed to be a next-generation, AI-driven development environment and editor platform. It serves as a powerful foundational engine capable of autonomous coding, seamless terminal interactions, and deep system understanding, built to be a superior alternative to traditional AI IDE integrations.

**Current Workspace:** `/media/kyrie/SOCROOT`

---

## 🚀 Current State: The Foundation

We have successfully established a highly secure, production-grade infrastructure. This "bulletproof" starting environment is designed to support the complex requirements of an autonomous AI engine without configuration drift or security risks.

### Foundational Infrastructure

1.  **Master Initialization (`init_project.sh`)**:
    *   An idempotent bash script that handles the entire environment setup, virtual environments, and initial directory scaffolding for AI agents.
    *   State tracking via `.project_state.json` ensures consistent setups across restarts.

2.  **Secure Secret Management**:
    *   Zero plaintext credentials exist on disk. Secrets are managed via GPG encryption (`.env.gpg`), prompting only on the first run and decrypting securely into memory/temporary files during execution.

3.  **Advanced Developer Environment**:
    *   **DevContainers (`.devcontainer/`)**: Ensures an isolated, identical development environment across any machine, pre-configured with essential extensions.
    *   **Task Management (`justfile`)**: A modern command runner configured for rapid setup, testing, and secure environment cleanup.
    *   **Pre-commit Hooks (`.pre-commit-config.yaml`)**: Strict hooks installed to enforce code formatting (Black, Flake8) and proactively prevent the leaking of secrets (detect-secrets).

---

## 📂 Core Directory Structure

```text
/media/kyrie/SOCROOT/
├── cli.py                 # Entry point for testing the Agent Engine
├── engine/                # Core Agentic IDE components
│   ├── agent_orchestrator.py  # LangGraph state machine (Plan -> Execute -> Observe)
│   ├── mcp_gateway.py         # Model Context Protocol (MCP) client
│   ├── terminal_executor.py   # Secure bash command wrapper
│   └── workspace_context.py   # Reader for .cursorrules / .antigravityrules
├── .devcontainer/         # Dev container configuration for isolated environments
├── .gemini/antigravity/   # Scaffolding for AI agent context (skills, agents, mcp)
├── init_project.sh        # Master setup script
├── justfile               # Task runner configuration
├── PROJECT_SPEC.md        # High-level project definition and configuration
├── requirements.txt       # Engine dependencies (langgraph, langchain-core, etc.)
├── .env.template          # Template for required environment variables
└── HANDOFF.md             # This document
```

---

## 🛠️ How to Operate the System

1.  **Start the Environment:**
    ```bash
    source venv/bin/activate
    # Or open the project in an editor supporting DevContainers.
    ```
2.  **Test the Agent Engine:**
    ```bash
    python cli.py --prompt "Create a React login page"
    ```
3.  **Manage Secrets:**
    ```bash
    just decrypt  # Requires GPG passphrase to expose .env temporarily
    just encrypt  # Re-encrypts changes
    just lock     # Securely deletes the plaintext .env before closing the session
    ```

---

## ⏭️ Next Steps

With the foundational `engine` package and CLI entry point in place, the immediate next steps are:

1.  **LLM Integration**: Connect `agent_orchestrator.py` to an actual LLM (e.g., using `langchain-google-genai` or `langchain-openai`) to replace the mock logic.
2.  **Tool Binding**: Bind the `TerminalExecutor` and file system actions as valid tools for the LLM to invoke within the LangGraph flow.
3.  **MCP Gateway Implementation**: Fully implement `mcp_gateway.py` using the `modelcontextprotocol` Python SDK to discover and interact with external MCP servers (e.g., filesystem, git).

