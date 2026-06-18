#!/bin/bash
# health_check.sh - Verificação de saúde da aplicação
# Uso: ./health_check.sh
# Retorna 0 se OK, 1 se falhou

set -euo pipefail

APP_URL="http://127.0.0.1:8000"
TIMEOUT=10

check_service() {
    systemctl is-active --quiet estoque || return 1
}

check_nginx() {
    systemctl is-active --quiet nginx || return 1
}

check_postgres() {
    systemctl is-active --quiet postgresql || return 1
}

check_http() {
    # Segue redirects, falha se não 2xx/3xx
    curl -sf --max-time "$TIMEOUT" -o /dev/null -w "%{http_code}" "$APP_URL/" | grep -qE '^(2|3)[0-9]{2}$'
}

check_disk() {
    # Alerta se uso > 90%
    df /opt/estoque | awk 'NR==2 {gsub(/%/,"",$5); if ($5 > 90) exit 1}'
}

check_memory() {
    # Alerta se memória livre < 500MB
    free -m | awk 'NR==2 {if ($7 < 500) exit 1}'
}

main() {
    local failed=0

    echo "=== Health Check $(date) ==="

    check_service && echo "✓ Serviço estoque" || { echo "✗ Serviço estoque"; failed=1; }
    check_nginx && echo "✓ Nginx" || { echo "✗ Nginx"; failed=1; }
    check_postgres && echo "✓ PostgreSQL" || { echo "✗ PostgreSQL"; failed=1; }
    check_http && echo "✓ HTTP $APP_URL" || { echo "✗ HTTP $APP_URL"; failed=1; }
    check_disk && echo "✓ Disco OK" || { echo "⚠ Disco > 90%"; failed=1; }
    check_memory && echo "✓ Memória OK" || { echo "⚠ Memória livre < 500MB"; failed=1; }

    echo "================================"

    if [ $failed -eq 0 ]; then
        echo "STATUS: HEALTHY"
        exit 0
    else
        echo "STATUS: UNHEALTHY"
        exit 1
    fi
}

main "$@"
