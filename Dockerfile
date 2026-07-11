# syntax=docker/dockerfile:1
# Dockerfile — projeto_oms (WHO GHO → dbt star schema)
# Imagem leve para execução do pipeline dbt em container.

FROM python:3.12-slim-bookworm AS base

LABEL org.opencontainers.image.title="projeto_oms — WHO GHO → dbt Star Schema"
LABEL org.opencontainers.image.description="Pipeline dbt com DuckDB para dados de saúde da OMS"
LABEL org.opencontainers.image.source="https://github.com/rob3rto88/projeto_oms"

# Evita prompts interativos
ENV DEBIAN_FRONTEND=noninteractive \
    PIP_NO_INPUT=1 \
    PIP_ROOT_USER_ACTION=ignore

WORKDIR /app

# ---- Stage: dependencies ----
FROM base AS deps

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---- Stage: runtime ----
FROM deps AS runtime

COPY Makefile .
COPY scripts/init_test_db.py scripts/
COPY dbt/ dbt/

# Diretório para banco de dados (volume externo ou init)
RUN mkdir -p database

# Porta padrão para execução
CMD ["make", "build"]

# ---
# Uso:
#   docker build -t projeto-oms .
#   docker run --rm -v $(pwd)/database:/app/database projeto-oms
#   docker run --rm projeto-oms make ci   # CI target (cria DB de teste)
