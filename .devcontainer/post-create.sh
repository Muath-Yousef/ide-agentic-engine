#!/usr/bin/env bash
set -euo pipefail

echo "🚀 Setting up ide-agentic-engine development environment..."

# Install Python dependencies
cd /workspace
python3 -m venv venv
./venv/bin/pip install --upgrade pip --quiet
./venv/bin/pip install -e ".[dev]" --quiet

# Install pre-commit hooks
./venv/bin/pre-commit install

# Decrypt secrets if SOPS key is available
if command -v sops &>/dev/null && [ -f .env.enc ]; then
    if sops -d .env.enc > .env 2>/dev/null; then
        echo "✅ Secrets decrypted"
    else
        echo "⚠️  Could not decrypt secrets (SOPS key not configured)"
    fi
fi

# Create required directories
mkdir -p reports/output knowledge/evidence knowledge/client_profiles

# Run self-check
./venv/bin/ide-agent self-check 2>/dev/null || true

echo ""
echo "✅ Environment ready!"
echo "   Run: just --list   (to see all commands)"
echo "   Run: just scan --client myClient --target example.com"
