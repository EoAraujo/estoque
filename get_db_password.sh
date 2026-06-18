#!/bin/bash
# get_db_password.sh - Recupera a senha do banco de dados
# Uso: ./get_db_password.sh

set -euo pipefail

ENV_FILE="/opt/estoque/.env"

if [ ! -f "$ENV_FILE" ]; then
    echo "Arquivo .env não encontrado em $ENV_FILE"
    exit 1
fi

echo "=== Configuração do Banco ==="
echo ""

# Extrai informações do .env
DB_URL=$(grep "^DATABASE_URL=" "$ENV_FILE" | cut -d'=' -f2-)

if [ -z "$DB_URL" ]; then
    echo "DATABASE_URL não configurado no .env"
    exit 1
fi

# Parse da URL: postgres://USER:PASS@HOST:DBNAME
# Remove o prefixo postgres://
TEMP=${DB_URL#postgres://}
TEMP=${TEMP#postgresql://}

# Extrai componentes
DB_USER=$(echo "$TEMP" | cut -d':' -f1)
DB_PASS=$(echo "$TEMP" | cut -d':' -f2 | cut -d'@' -f1)
DB_HOST=$(echo "$TEMP" | cut -d'@' -f2 | cut -d':' -f1)
DB_PORT=$(echo "$TEMP" | cut -d'@' -f2 | cut -d':' -f2 | cut -d'/' -f1)
DB_NAME=$(echo "$TEMP" | cut -d'/' -f2 | cut -d'?' -f1)

echo "Usuário: $DB_USER"
echo "Senha: $DB_PASS"
echo "Host: $DB_HOST"
echo "Porta: $DB_PORT"
echo "Banco: $DB_NAME"
echo ""

# Testa conexão
echo "Testando conexão..."
if PGPASSWORD="$DB_PASS" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" >/dev/null 2>&1; then
    echo "✓ Conexão OK!"
else
    echo "✗ Falha na conexão. Verifique se o PostgreSQL está rodando."
fi
