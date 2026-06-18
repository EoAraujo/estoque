#!/bin/bash
# deploy.sh - Atualização automática da aplicação em produção
# Uso: ./deploy.sh
# Coloque em /opt/estoque/deploy.sh e dê permissão: chmod +x deploy.sh

set -euo pipefail

APP_DIR="/opt/estoque"
VENV_DIR="$APP_DIR/.venv"
LOG_FILE="$APP_DIR/deploy.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

error() {
    log "ERRO: $*"
    exit 1
}

log "=== Iniciando deploy ==="

# 1. Verifica se está no diretório correto
cd "$APP_DIR" || error "Diretório $APP_DIR não encontrado"

# 2. Para o serviço (zero downtime não é crítico aqui)
log "Parando serviço..."
sudo systemctl stop estoque || error "Falha ao parar serviço"

# 3. Atualiza código
log "Puxando atualizações do Git..."
git pull origin main || error "Falha no git pull"

# 4. Ativa venv
source "$VENV_DIR/bin/activate" || error "Falha ao ativar venv"

# 5. Atualiza dependências Python
log "Instalando dependências Python..."
pip install --upgrade pip >/dev/null
pip install -r requirements.txt >> "$LOG_FILE" 2>&1 || error "Falha no pip install"

# 6. Atualiza dependências Node e compila CSS
log "Compilando CSS (Tailwind)..."
if command -v npm >/dev/null 2>&1; then
    npm ci >> "$LOG_FILE" 2>&1 || error "Falha no npm ci"
    npm run build:css >> "$LOG_FILE" 2>&1 || error "Falha no build:css"
else
    log "AVISO: npm não encontrado, pulando build do CSS"
fi

# 7. Migrações
log "Aplicando migrações..."
python manage.py migrate >> "$LOG_FILE" 2>&1 || error "Falha nas migrações"

# 8. Coleta estáticos
log "Coletando arquivos estáticos..."
python manage.py collectstatic --noinput >> "$LOG_FILE" 2>&1 || error "Falha no collectstatic"

# 9. Reinicia serviço
log "Reiniciando serviço..."
sudo systemctl start estoque || error "Falha ao iniciar serviço"

# 10. Aguarda subir e verifica health
sleep 3
if systemctl is-active --quiet estoque; then
    log "Serviço ativo ✓"
else
    error "Serviço NÃO subiu - verifique journalctl -u estoque"
fi

# 11. Teste rápido de health check
if curl -sf http://127.0.0.1:8000/ >/dev/null; then
    log "Health check OK ✓"
else
    log "AVISO: Health check falhou (pode ser normal se DEBUG=False e ALLOWED_HOSTS não inclui localhost)"
fi

log "=== Deploy concluído com sucesso ==="
