#!/bin/bash
set -e

echo "🚀 Running post-create setup..."

# Install basic tools
sudo apt-get update && sudo apt-get install -y gnupg jq curl age

# Install Python dependencies
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
fi

# Install pre-commit
pip install pre-commit
pre-commit install

# Verify setup
./init_project.sh --verify

echo "✅ DevContainer setup complete."
