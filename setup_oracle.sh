#!/bin/bash
# setup_oracle.sh - Setup completo para Oracle Cloud Ubuntu
# Uso: ./setup_oracle.sh
# Execute como root ou com sudo

set -euo pipefail

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] $*${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] AVISO: $*${NC}"
}

error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERRO: $*${NC}"
    exit 1
}

# Verifica se é root
if [ "$EUID" -ne 0 ]; then
    error "Execute como root: sudo ./setup_oracle.sh"
fi

APP_DIR="/opt/estoque"
DB_NAME="estoque"
DB_USER="estoque_user"
DB_PASS="estoque_$(openssl rand -hex 8)"  # Senha aleatória

log "=== Setup Oracle Cloud - Estoque Cozinha ==="
log "Diretório: $APP_DIR"
log "Banco: $DB_NAME"
log "Usuário DB: $DB_USER"
log ""

# 1. Atualiza sistema
log "1/12 Atualizando sistema..."
apt update -qq
apt upgrade -y -qq

# 2. Instala dependências
log "2/12 Instalando dependências..."
apt install -y -qq \
    python3.11 python3.11-venv python3.11-dev python3-pip \
    postgresql postgresql-contrib \
    nginx \
    certbot python3-certbot-nginx \
    git curl build-essential libpq-dev \
    ufw fail2ban

# 3. Node.js 20
log "3/12 Instalando Node.js 20..."
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt install -y -qq nodejs

# 4. Configura PostgreSQL
log "4/12 Configurando PostgreSQL..."
systemctl enable postgresql
systemctl start postgresql

# Verifica se usuário já existe
USER_EXISTS=$(sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'" 2>/dev/null || echo "0")

if [ "$USER_EXISTS" = "1" ]; then
    log "Usuário $DB_USER já existe. Gerando nova senha..."
    DB_PASS="estoque_$(openssl rand -hex 8)"
    sudo -u postgres psql -c "ALTER USER $DB_USER WITH PASSWORD '$DB_PASS';"
    log "Senha atualizada!"
else
    log "Criando usuário $DB_USER..."
    sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASS';"
fi

# Verifica se banco já existe
DB_EXISTS=$(sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" 2>/dev/null || echo "0")

if [ "$DB_EXISTS" = "1" ]; then
    log "Banco $DB_NAME já existe."
else
    log "Criando banco $DB_NAME..."
    sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"
fi

# Garante permissões
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"
sudo -u postgres psql -c "ALTER DATABASE $DB_NAME OWNER TO $DB_USER;"

log "PostgreSQL configurado!"
log "Usuário: $DB_USER"
log "Senha: $DB_PASS"
log "Guarde esta senha!"

# 5. Clona ou prepara repositório
log "5/12 Preparando aplicação..."
if [ -d "$APP_DIR/.git" ]; then
    cd "$APP_DIR"
    git pull origin main
else
    # Se não existe, assume que os arquivos já estão lá
    if [ ! -d "$APP_DIR" ]; then
        error "Diretório $APP_DIR não encontrado. Copie os arquivos primeiro."
    fi
    cd "$APP_DIR"
fi

# 6. Configura Python
log "6/12 Configurando Python..."
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q

# 7. Configura Node
log "7/12 Compilando CSS..."
npm install -q
npm run build:css

# 8. Gera chaves VAPID
log "8/12 Gerando chaves VAPID..."
chmod +x generate_vapid.sh
./generate_vapid.sh

# 9. Cria .env
log "9/12 Criando .env..."
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(50))")
PUBLIC_IP=$(curl -s http://ifconfig.me)

cat > .env << EOF
DEBUG=False
SECRET_KEY=$SECRET_KEY
ALLOWED_HOSTS=$PUBLIC_IP,localhost,127.0.0.1
DATABASE_URL=postgres://$DB_USER:$DB_PASS@localhost:5432/$DB_NAME
VAPID_PRIVATE_KEY_FILE=/opt/estoque/keys/vapid_private.pem
VAPID_PUBLIC_KEY_FILE=/opt/estoque/keys/vapid_public.key
VAPID_CLAIMS_SUB=mailto:admin@estoque.local
CSRF_TRUSTED_ORIGINS=$PUBLIC_IP
LOG_LEVEL=INFO
EOF

chmod 600 .env

# 10. Migrações
log "10/12 Aplicando migrações..."
python manage.py migrate --noinput
python manage.py collectstatic --noinput

# 11. Cria superuser
log "11/12 Criando superuser admin..."
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@local', 'admin123', first_name='Admin', last_name='Sistema')
    print('Superuser admin criado com sucesso!')
else:
    print('Superuser admin já existe.')
"

# 12. Configura serviços
log "12/12 Configurando serviços..."

# Copia service files
cp estoque.service /etc/systemd/system/
cp backup.service /etc/systemd/system/
cp backup.timer /etc/systemd/system/

# Permissões
chmod +x deploy.sh backup_prod.sh health_check.sh

# Reload systemd
systemctl daemon-reload

# Habilita serviços
systemctl enable --now estoque
systemctl enable --now backup.timer

# Configura UFW
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

# Configura fail2ban
systemctl enable fail2ban
systemctl start fail2ban

# Testa serviço
sleep 3
if systemctl is-active --quiet estoque; then
    log "Serviço estoque ativo!"
else
    warn "Serviço estoque pode não estar rodando. Verifique: journalctl -u estoque"
fi

log ""
log "=== SETUP CONCLUÍDO ==="
log ""
log "Próximos passos:"
log "1. Acesse: http://$PUBLIC_IP/"
log "2. Login: admin / admin123"
log "3. Para HTTPS, configure domínio e rode: sudo certbot --nginx -d seu-dominio.com"
log "4. Altere a senha do admin no Django Admin"
log ""
log "Comandos úteis:"
log "  systemctl status estoque    # Ver status"
log "  journalctl -u estoque -f    # Ver logs"
log "  /opt/estoque/deploy.sh      # Atualizar"
log "  /opt/estoque/backup_prod.sh # Backup manual"
log "  /opt/estoque/health_check.sh # Verificar saúde"
log ""
log "Guarde a senha do banco: $DB_PASS"
log ""
