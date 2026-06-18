#!/bin/bash
# backup_prod.sh - Backup automatizado PostgreSQL para produção
# Uso: ./backup_prod.sh
# Agende no crontab: 0 3 * * * /opt/estoque/backup_prod.sh >> /opt/estoque/backups/cron.log 2>&1

set -euo pipefail

APP_DIR="/opt/estoque"
BACKUP_DIR="$APP_DIR/backups"
DATE=$(date +%F_%H-%M-%S)
DB_NAME="estoque"
DB_USER="estoque_user"
RETENTION_DAYS=30

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

# Cria diretório se não existe
mkdir -p "$BACKUP_DIR"

log "Iniciando backup do banco $DB_NAME..."

# Dump do PostgreSQL
# --no-owner: não inclui comandos de ownership (evita erro ao restaurar em outro user)
# --clean: inclui DROP antes de CREATE
# --if-exists: evita erro se objeto não existe
# --no-acl: não inclui GRANT/REVOKE
pg_dump --no-owner --clean --if-exists --no-acl \
    -U "$DB_USER" -d "$DB_NAME" \
    > "$BACKUP_DIR/estoque-${DATE}-pg.sql" 2>>"$BACKUP_DIR/backup_errors.log"

# Verifica se o dump tem tamanho razoável (>1KB)
SIZE=$(stat -c%s "$BACKUP_DIR/estoque-${DATE}-pg.sql" 2>/dev/null || echo 0)
if [ "$SIZE" -lt 1024 ]; then
    log "AVISO: Backup muito pequeno ($SIZE bytes) - possível falha"
    exit 1
fi

# Comprime
gzip "$BACKUP_DIR/estoque-${DATE}-pg.sql"
log "Backup salvo: ${BACKUP_DIR}/estoque-${DATE}-pg.sql.gz ($(du -h "$BACKUP_DIR/estoque-${DATE}-pg.sql.gz" | cut -f1))"

# Remove backups antigos (retention)
log "Removendo backups com mais de ${RETENTION_DAYS} dias..."
find "$BACKUP_DIR" -name "estoque-*-pg.sql.gz" -mtime +"$RETENTION_DAYS" -delete

# Lista backups atuais
log "Backups atuais:"
ls -lh "$BACKUP_DIR"/estoque-*-pg.sql.gz 2>/dev/null | tail -5

log "Backup concluído ✓"
