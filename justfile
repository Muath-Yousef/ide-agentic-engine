# Taskfile/Just for SOC Root
version: '3'

vars:
  VENV: "venv"

default:
    @just --list

# First-time project setup
setup:
    ./init_project.sh
    @pre-commit install
    @echo "✅ Project setup complete."

# Run a security scan
scan target:
    ./venv/bin/python3 main_orchestrator.py --target {{target}}

# Run tests
test:
    ./venv/bin/pytest tests/ -v

# Cleanup environment
clean:
    rm -rf venv/
    rm -f .env
    @echo "🧹 Environment cleaned."

# Verify evidence chain integrity
verify-evidence:
    ./venv/bin/python3 -c "from soc.evidence_store import verify_all_chains; verify_all_chains()"
