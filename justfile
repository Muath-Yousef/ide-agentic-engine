set dotenv-load := true

# Show all available commands
default:
    @just --list

# First-time project setup
setup:
    uv sync --all-extras
    uv run pre-commit install
    -sops -d .env.enc > .env 2>/dev/null
    docker-compose -f deployment/docker-compose.yml up -d redis jaeger prometheus grafana
    @echo "✅ Setup complete. Run: just self-check"

# Validate environment
self-check:
    PYTHONPATH=. uv run ide-agent self-check

# Run a full security scan
scan client domain:
    PYTHONPATH=. uv run ide-agent scan --client {{client}} --target {{domain}}

# Run compliance analysis only
compliance client:
    PYTHONPATH=. uv run ide-agent compliance --client {{client}}

# Show engine status
status:
    PYTHONPATH=. uv run ide-agent status

# Run tests with coverage
test:
    PYTHONPATH=. uv run pytest tests/ -v --cov=engine --cov=agents --cov=core --cov-report=html --cov-report=term-missing

# Run tests fast (no coverage, stop on first failure)
test-fast:
    PYTHONPATH=. uv run pytest tests/ -v -x --no-cov

# Format all Python files
fmt:
    uv run black engine/ agents/ core/ tools/ socroot/ tests/
    uv run isort engine/ agents/ core/ tools/ socroot/ tests/

# Lint
lint:
    uv run flake8 engine/ agents/ core/ tools/ socroot/ --max-line-length=100
    uv run mypy engine/ agents/ core/

# Decrypt secrets
secrets-decrypt:
    sops -d .env.enc > .env
    @echo "✅ .env decrypted"

# Encrypt secrets
secrets-encrypt:
    sops -e .env > .env.enc
    @echo "✅ .env.enc updated — commit this file, NOT .env"

# Backup evidence and profiles to S3
backup:
    bash scripts/backup_everything.sh

# Deploy to production
deploy: test
    ansible-playbook -i deployment/inventory/production deployment/deploy.yml

# Watch logs from all services
logs:
    docker-compose -f deployment/docker-compose.yml logs -f

# Stop all services
stop:
    docker-compose -f deployment/docker-compose.yml down
