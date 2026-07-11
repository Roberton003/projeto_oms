#!/usr/bin/env bash
# ==========================================================
# bootstrap.sh — projeto_oms
# Configura ambiente local a partir de um clone fresco.
# Uso: bash scripts/bootstrap.sh
# ==========================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

echo "=== projeto_oms bootstrap ==="
echo ""

# 1. Create virtualenv
if [ ! -d venv ]; then
    echo "[1/4] Criando virtualenv..."
    python3 -m venv venv
else
    echo "[1/4] virtualenv já existe."
fi

# 2. Install Python dependencies
echo "[2/4] Instalando dependências Python..."
venv/bin/pip install -q --upgrade pip
venv/bin/pip install -q -r requirements.txt

# 3. Copy config template if missing
if [ ! -f dbt/profiles.yml ]; then
    echo "[3/4] profiles.yml não encontrado, copiando template..."
    cp dbt/profiles.example.yml dbt/profiles.yml 2>/dev/null || true
fi

# 4. Install dbt packages
echo "[4/4] Instalando pacotes dbt..."
venv/bin/dbt deps --project-dir dbt

echo ""
echo "=== Bootstrap completo ==="
echo ""
echo "Comandos úteis:"
echo "  source venv/bin/activate"
echo "  make build                  # dbt build (default: dev)"
echo "  make ci                     # dbt build (target: ci)"
echo "  DBT_TARGET=ci make build    # build para CI"
echo ""
