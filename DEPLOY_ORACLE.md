# Deploy Oracle Cloud - Estoque Cozinha

## Pré-requisitos

1. Conta Oracle Cloud (https://cloud.oracle.com)
2. VM Ubuntu 22.04 ARM (VM.Standard.A1.Flex) criada
3. SSH key (ssh-key-2026-06-18.key)
4. IP público: 64.181.168.121

## Passo a passo

### 1. Conectar na VM

```bash
chmod 400 ssh-key-2026-06-18.key
ssh -i ssh-key-2026-06-18.key ubuntu@64.181.168.121
```

### 2. Copiar arquivos para a VM

```bash
# No seu PC (PowerShell)
scp -i ssh-key-2026-06-18.key -r C:\Users\Administrator\Desktop\Estoque\* ubuntu@64.181.168.121:/tmp/estoque/
```

### 3. Executar setup na VM

```bash
# Na VM
sudo su
mkdir -p /opt/estoque
cp -r /tmp/estoque/* /opt/estoque/
cd /opt/estoque
chmod +x setup_oracle.sh
./setup_oracle.sh
```

### 4. Acessar o sistema

- URL: http://64.181.168.121/
- Login: admin
- Senha: admin123

### 5. Configurar HTTPS (opcional, mas recomendado)

```bash
# Se tiver domínio apontando para 64.181.168.121
sudo certbot --nginx -d estoque.seudominio.com
```

## Arquivos importantes

| Arquivo | Função |
|---------|--------|
| `.env` | Configurações de produção (NÃO versionar) |
| `estoque.service` | Systemd service do gunicorn |
| `backup.service` | Systemd service de backup |
| `backup.timer` | Timer para backup diário |
| `deploy.sh` | Script de atualização |
| `backup_prod.sh` | Script de backup |
| `health_check.sh` | Verificação de saúde |

## Comandos úteis

```bash
# Status do sistema
systemctl status estoque nginx postgresql

# Logs
journalctl -u estoque -f

# Backup manual
/opt/estoque/backup_prod.sh

# Deploy update
cd /opt/estoque
git pull
./deploy.sh

# Health check
/opt/estoque/health_check.sh

# Recuperar senha do banco
/opt/estoque/get_db_password.sh

# Reiniciar serviços
sudo systemctl restart estoque nginx postgresql
```

## Erros comuns

### "role already exists"
O script setup já foi executado antes. O script agora verifica se usuário/banco já existem.
Se quiser reconfigurar do zero:
```bash
sudo -u postgres psql -c "DROP DATABASE IF EXISTS estoque;"
sudo -u postgres psql -c "DROP USER IF EXISTS estoque_user;"
./setup_oracle.sh
```

### "password authentication failed"
Recupere a senha com:
```bash
/opt/estoque/get_db_password.sh
```

## Backup

O backup automático roda diariamente às 03:00.

Para backup manual:
```bash
/opt/estoque/backup_prod.sh
```

Backups ficam em `/opt/estoque/backups/` com retenção de 30 dias.

## Segurança

- Senha aleatória para PostgreSQL gerada no setup
- Chaves VAPID geradas automaticamente
- HTTPS deve ser configurado via Let's Encrypt
- UFW habilitado (portas 22, 80, 443)
- fail2ban habilitado

## Troubleshooting

### Serviço não inicia
```bash
journalctl -u estoque -n 50
systemctl status estoque
```

### Erro de conexão com banco
```bash
systemctl status postgresql
sudo -u postgres psql -c "\l"  # Lista bancos
```

### Nginx não responde
```bash
nginx -t  # Testa configuração
systemctl status nginx
tail -f /var/log/nginx/error.log
```

### Backup falhou
```bash
cat /opt/estoque/backups/backup_errors.log
/opt/estoque/backup_prod.sh  # Testa manual
```
