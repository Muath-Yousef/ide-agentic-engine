#!/bin/bash
# Sync .shared-secrets.env → api_keys.yaml
# Run this whenever you change any API key

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SECRETS_FILE=~/Projects/.shared-secrets.env
YAML_FILE="$SCRIPT_DIR/api_keys.yaml"

if [ ! -f "$SECRETS_FILE" ]; then
    echo "❌ Secrets file not found: $SECRETS_FILE"
    exit 1
fi

source "$SECRETS_FILE"

python3 - << PYEOF
import yaml, os, sys

yaml_path = "$YAML_FILE"

with open(yaml_path) as f:
    data = yaml.safe_load(f)

updates = {
    'groq':    os.environ.get('GROQ_API_KEY'),
    'openai':  os.environ.get('OPENAI_API_KEY'),
    'gemini':  os.environ.get('GEMINI_API_KEY'),
}

for provider, key in updates.items():
    if key:
        if provider not in data['services']:
            data['services'][provider] = {'keys': [{'value': key, 'status': 'active', 'retry_after': None}]}
        else:
            # Update first active key or add new one
            data['services'][provider]['keys'][0]['value'] = key
            data['services'][provider]['keys'][0]['status'] = 'active'
            data['services'][provider]['keys'][0]['retry_after'] = None
        print(f"  ✅ {provider}: updated ({len(key)} chars)")
    else:
        print(f"  ⚠️  {provider}: key not found in secrets, skipping")

with open(yaml_path, 'w') as f:
    yaml.dump(data, f, default_flow_style=False)

print("\n✅ api_keys.yaml synced from .shared-secrets.env")
PYEOF
