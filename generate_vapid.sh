#!/bin/bash
# generate_vapid.sh - Gera chaves VAPID e salva em arquivo separado
# Uso: ./generate_vapid.sh

set -euo pipefail

VENV_DIR="/opt/estoque/.venv"
KEYS_DIR="/opt/estoque/keys"
PRIV_FILE="$KEYS_DIR/vapid_private.pem"
PUB_FILE="$KEYS_DIR/vapid_public.key"

# Cria diretório
mkdir -p "$KEYS_DIR"
chmod 700 "$KEYS_DIR"

# Gera chaves
source "$VENV_DIR/bin/activate"

python3 << 'EOF'
import os
from py_vapid import Vapid02
from cryptography.hazmat.primitives import serialization
import base64

keys_dir = "/opt/estoque/keys"
priv_file = os.path.join(keys_dir, "vapid_private.pem")
pub_file = os.path.join(keys_dir, "vapid_public.key")

# Gera chaves
vapid = Vapid02()
vapid.generate_keys()

# Salva chave privada (PEM)
with open(priv_file, "wb") as f:
    f.write(vapid.private_pem())

# Salva chave pública (urlsafe base64)
raw = vapid._public_key.public_bytes(
    serialization.Encoding.X962,
    serialization.PublicFormat.UncompressedPoint,
)
pub_b64 = base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")

with open(pub_file, "w") as f:
    f.write(pub_b64)

# Permissões
os.chmod(priv_file, 0o600)
os.chmod(pub_file, 0o644)

print(f"Chaves geradas:")
print(f"  Privada: {priv_file}")
print(f"  Pública: {pub_file}")
EOF

# Atualiza .env (remove linhas VAPID antigas e adiciona referências)
ENV_FILE="/opt/estoque/.env"

# Remove linhas VAPID antigas do .env
sed -i '/^VAPID_PRIVATE_KEY=/d' "$ENV_FILE"
sed -i '/^VAPID_PUBLIC_KEY=/d' "$ENV_FILE"

# Adiciona referências aos arquivos
echo "" >> "$ENV_FILE"
echo "# Chaves VAPID (armazenadas em /opt/estoque/keys/)" >> "$ENV_FILE"
echo "VAPID_PRIVATE_KEY_FILE=$PRIV_FILE" >> "$ENV_FILE"
echo "VAPID_PUBLIC_KEY_FILE=$PUB_FILE" >> "$ENV_FILE"

echo ""
echo "Chaves VAPID configuradas!"
echo "Arquivo .env atualizado com referências aos arquivos de chave."
