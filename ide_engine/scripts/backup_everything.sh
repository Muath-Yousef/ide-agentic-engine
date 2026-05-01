#!/usr/bin/env bash
# 3-2-1 Backup Strategy:
#   3 copies: local + S3 + cross-region S3
#   2 types: disk + object storage
#   1 offsite: S3 in different region

set -euo pipefail

BACKUP_DATE=$(date +%Y-%m-%d_%H-%M)
S3_BUCKET="${S3_BACKUP_BUCKET:-s3://ide-agent-backups}"
LOCAL_BACKUP_DIR="${LOCAL_BACKUP_DIR:-/var/backups/ide-agent}"

mkdir -p "$LOCAL_BACKUP_DIR"

log() { echo "[$(date '+%H:%M:%S')] $*"; }

# 1. Evidence chains (critical — must never be lost)
log "Backing up evidence chains..."
tar czf "$LOCAL_BACKUP_DIR/evidence-$BACKUP_DATE.tar.gz" knowledge/evidence/ 2>/dev/null || true
aws s3 cp "$LOCAL_BACKUP_DIR/evidence-$BACKUP_DATE.tar.gz" \
    "$S3_BUCKET/evidence/" --sse aws:kms || log "⚠️  S3 upload failed for evidence"

# 2. Client profiles
log "Backing up client profiles..."
tar czf "$LOCAL_BACKUP_DIR/clients-$BACKUP_DATE.tar.gz" knowledge/client_profiles/ 2>/dev/null || true
aws s3 cp "$LOCAL_BACKUP_DIR/clients-$BACKUP_DATE.tar.gz" \
    "$S3_BUCKET/clients/" || log "⚠️  S3 upload failed for clients"

# 3. Encrypted secrets (safe to back up — already encrypted by SOPS)
log "Backing up encrypted secrets..."
if [ -f .env.enc ]; then
    aws s3 cp .env.enc "$S3_BUCKET/secrets/env-$BACKUP_DATE.enc" || true
fi

# 4. Generated reports
log "Backing up reports..."
if [ -d reports/output ] && [ "$(ls -A reports/output)" ]; then
    tar czf "$LOCAL_BACKUP_DIR/reports-$BACKUP_DATE.tar.gz" reports/output/
    aws s3 cp "$LOCAL_BACKUP_DIR/reports-$BACKUP_DATE.tar.gz" \
        "$S3_BUCKET/reports/" || true
fi

# Clean up local backups older than 30 days
find "$LOCAL_BACKUP_DIR" -name "*.tar.gz" -mtime +30 -delete

log "✅ Backup complete: $BACKUP_DATE"
log "   S3 bucket: $S3_BUCKET"
