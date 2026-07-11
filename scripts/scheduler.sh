#!/usr/bin/env bash
# ==========================================================
# scheduler.sh — Execução agendada do pipeline
# Uso:
#   bash scripts/scheduler.sh              # roda uma vez
#   bash scripts/scheduler.sh --daemon     # modo contínuo (cron interno)
#   bash scripts/scheduler.sh --airflow    # gera metadados para Airflow
#
# Para agendar no crontab (execução diária às 8h):
#   0 8 * * * /path/to/projeto_oms/scripts/scheduler.sh --ci >> /path/to/projeto_oms/logs/scheduler.log 2>&1
# ==========================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

# Timestamp ISO 8601
TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
LOG_DIR="logs"
mkdir -p "$LOG_DIR"

log() {
    local level="$1"
    shift
    echo "{\"ts\":\"$TS\",\"level\":\"$level\",\"message\":\"$*\",\"pipeline\":\"oms_scheduler\"}"
}

cleanup() {
    log "INFO" "Scheduler finalizado (exit code: $1)"
    exit "$1"
}
trap 'cleanup $?' EXIT

log "INFO" "Iniciando pipeline OMS (target=$DBT_TARGET)"

# Verifica se raw DB existe; se nao, tenta init
RAW_DB="${DBT_RAW_DB:-${PROJECT_DIR}/database/who_gho.db}"
if [ ! -f "$RAW_DB" ]; then
    log "WARN" "Raw DB nao encontrado em $RAW_DB — executando init"
    python3 "${SCRIPT_DIR}/init_test_db.py"
fi

# Executa CI
log "INFO" "Executando make ci..."
if make ci 2>&1; then
    log "INFO" "Pipeline concluido com sucesso"
    
    # Gera relatorio de saude pos-execucao
    if [ -f "${SCRIPT_DIR}/health_check.py" ]; then
        python3 "${SCRIPT_DIR}/health_check.py" --json >> "$LOG_DIR/health.jsonl"
    fi
else
    log "ERROR" "Pipeline falhou"
    # Em modo daemon, nao propaga erro para nao travar o cron
    if [ "${1:-}" != "--daemon" ]; then
        exit 1
    fi
fi

log "INFO" "Pipeline finalizado"
