#!/usr/bin/env bash
# First-time secrets setup: generate Age key, create .env template, encrypt.
set -euo pipefail

echo "🔐 Setting up SOPS + Age encryption..."

# Install age if missing
if ! command -v age &>/dev/null; then
    echo "Installing age..."
    curl -Lo /tmp/age.tar.gz \
        https://github.com/FiloSottile/age/releases/latest/download/age-v1.1.1-linux-amd64.tar.gz
    tar xf /tmp/age.tar.gz -C /tmp
    sudo mv /tmp/age/age* /usr/local/bin/
fi

# Install sops if missing
if ! command -v sops &>/dev/null; then
    echo "Installing sops..."
    curl -Lo /usr/local/bin/sops \
        https://github.com/mozilla/sops/releases/latest/download/sops-v3.8.1.linux.amd64
    chmod +x /usr/local/bin/sops
fi

# Generate Age key
KEY_DIR="$HOME/.config/sops/age"
KEY_FILE="$KEY_DIR/keys.txt"
mkdir -p "$KEY_DIR"

if [ ! -f "$KEY_FILE" ]; then
    age-keygen -o "$KEY_FILE"
    echo "✅ Age key generated: $KEY_FILE"
else
    echo "ℹ️  Using existing Age key: $KEY_FILE"
fi

PUBLIC_KEY=$(grep "public key:" "$KEY_FILE" | awk '{print $NF}')
echo "   Public key: $PUBLIC_KEY"

# Update .sops.yaml with the public key
if [ -f .sops.yaml ]; then
    sed -i "s/age1REPLACE_WITH_YOUR_PUBLIC_KEY/$PUBLIC_KEY/g" .sops.yaml
    echo "✅ .sops.yaml updated"
fi

# Create .env template if not exists
if [ ! -f .env ]; then
    cat > .env << 'EOF'
ANTHROPIC_API_KEY=your_anthropic_api_key_here
REDIS_URL=redis://localhost:6379/0
SENTRY_DSN=
OTLP_ENDPOINT=http://localhost:4317
WAZUH_API_URL=https://wazuh.local:55000
WAZUH_API_USER=wazuh-api
WAZUH_API_PASSWORD=
N8N_URL=http://localhost:5678
N8N_API_KEY=
SEARCH_API_KEY=
GDRIVE_MCP_TOKEN=
S3_BACKUP_BUCKET=s3://your-backup-bucket
GRAFANA_PASSWORD=changeme
REDIS_PASSWORD=changeme
ENVIRONMENT=development
EOF
    echo "✅ .env template created — fill in your values, then run: just secrets-encrypt"
fi

echo ""
echo "📋 Next steps:"
echo "   1. Edit .env with your actual API keys"
echo "   2. Run: sops -e .env > .env.enc"
echo "   3. Run: git add .env.enc .sops.yaml"
echo "   4. Add .env to .gitignore (already should be)"
echo ""
echo "   Store your Age private key safely: $KEY_FILE"
