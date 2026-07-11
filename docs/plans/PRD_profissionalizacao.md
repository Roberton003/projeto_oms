# PRD — Profissionalização do projeto_oms (WHO GHO Data Warehouse)

> **Constitution:** Phase Gates referem-se aos Artigos III, IV, VI e VII da Spec Constitution do harness opencode.
> **Origem:** Plano de carreira Roberto (Claude Code, 08/07/2026). Prioridade 2 de 4 — menor esforço, fecha o gap de dbt do portfólio.
> **Executor:** opencode + agentes. **Revisor:** Claude Code por épico.

---

## Contexto

Auditoria (08/07/2026): o repo tem o melhor data quality do portfólio (Great Expectations com 3 suites reais wired no DAG) e boa documentação (docs/01–04, DATA_CATALOG), mas:

- **Sem dbt** — o star schema Kimball é construído por DDL/DML manual em `scripts/create_database.py` via `sqlite3`. O LinkedIn/CV de Roberto cita dbt sem evidência pública; este repo é o lugar natural de fechar esse gap.
- **Não idempotente** — `create_database.py` faz `DROP TABLE IF EXISTS` + rebuild total a cada run do DAG `@daily`.
- **DAG não portável** — `dags/oms_data_pipeline.py` usa BashOperator com paths absolutos hardcoded (`/mnt/arquivos/.../venv/bin/python`); não roda em outra máquina/container.
- **Sem testes pytest, sem CI** — únicos "testes" são smoke scripts GX (`test_gx_connection.py`, `test_region_endpoint.py`).
- **Dockerfile documentado mas inexistente** — `docs/02_docker_containerization.md` descreve containerização que não está no repo (há só um gerador `create_dockerfile.py`).
- CSVs/JSON de dados brutos commitados (529K em `data/`) — blur na história "ingere da API".

## Objetivo

DW com transformações em **dbt** (models + tests + docs), carga **incremental idempotente**, DAG portável, containerizado e com CI. Critério de sucesso: `dbt build` verde com testes + os Critérios de Aceite finais.

## Escopo

### Incluído
Épicos 1–5 abaixo.

### Fora de Escopo
- Migrar de SQLite para Postgres/BigQuery (SQLite/DuckDB local é adequado ao propósito demo — documentar como limitação declarada no README).
- Novos indicadores/domínios da API OMS.
- Dashboard/camada de visualização.

---

## Épicos (ordem de execução)

### Épico 1 — Higiene de dados versionados (bloqueante) ✅
- [x] Remover `data/*.csv`/`*.json` do git (mantê-los como fixtures de teste pequenas em `tests/fixtures/` se necessários pro CI (Épico 5), com nota explícita).
- [x] `README`: seção "Como obter os dados" (script de ingestão da API OData).
- [x] Remover `linkedin_post.txt`, `populate_database.log`, `simple_auth_manager_passwords.json.generated` e afins do repo (gitignore + remoção do índice).

### Épico 2 — dbt core do star schema
1. Criar projeto `dbt/` na raiz: **dbt-core + dbt-duckdb** (preferido sobre adapter sqlite: mais maduro, e DuckDB lê o SQLite existente via extensão ou stage em Parquet — decidir e documentar em 1 parágrafo no README do dbt).
2. Models: `staging/stg_indicators.sql`, `stg_dimensions.sql` (fontes = saída bruta da ingestão `coleta_oms.py`) → `marts/dim_indicator.sql`, `dim_location.sql`, `dim_time.sql`, `fct_observations.sql` — replicando o schema atual de `create_database.py`.
3. Testes dbt: `unique` + `not_null` nas surrogate keys, `relationships` fact→dims, `accepted_values` onde o DATA_CATALOG define domínio.
4. `dbt docs generate` funcionando; screenshot da linhagem no README.
5. Aposentar o DDL manual: `create_database.py` reduzido a bootstrap da camada raw (ou deletado se dbt seeds/staging cobrirem); `populate_database.py` passa a carregar apenas raw.

### Épico 3 — Idempotência e carga incremental
1. `fct_observations` como **modelo incremental dbt** (`materialized='incremental'`, `unique_key` = chave natural indicador+localização+período), com watermark pela data de observação.
2. Dims como `materialized='table'` (dimensões pequenas, rebuild ok) — decisão documentada.
3. Teste de idempotência: rodar `dbt build` 2× sobre o mesmo raw → contagem de linhas do fact idêntica.
4. Documentar o padrão em `docs/05_incremental_idempotency.md`.

### Épico 4 — DAG portável
1. Reescrever `dags/oms_data_pipeline.py`: sem paths absolutos; tasks = ingestão (PythonOperator chamando módulo instalável ou `BashOperator` com `dbt build` relativo a env var `OMS_HOME`), depois validação GE.
2. Config via env vars (`.env.example` commitado).
3. As 3 suites GE continuam no fluxo (rodando pós-dbt sobre as tabelas finais).

### Épico 5 — Docker + CI
1. `Dockerfile` real na raiz (o que docs/02 descreve): imagem com deps + dbt, entrypoint parametrizável. Deletar `create_dockerfile.py`.
2. `.github/workflows/ci.yml`: lint (ruff), pytest (criar `tests/` com testes da ingestão usando fixture da API mockada), `dbt build --target ci` sobre fixture raw pequena, execução das GE suites.
3. Badge de CI no README.

---

## Phase Gates

### Simplicity Gate (Art. VI)
- [x] Cada model dbt faz UMA coisa (staging limpa; marts modelam); nenhum SQL >200 linhas esperado.
- [x] Raw → staging → marts equivale a bronze/silver/gold; desvio nominal documentado no README do dbt.
- [x] Sem god transform: fact e dims em models separados.

### Intentional Abstraction Gate (Art. VII)
- [x] dbt é framework nativo, não wrapper próprio.
- [x] Raw permanece acessível (camada raw preservada).
- [x] Contratos = schema.yml dos models com testes; dono = Roberto.

### Data Contract Gate (Art. III)
- [ ] `schema.yml` por model: colunas, tipos, nullability, testes (Épico 2.3).
- [x] Regras de qualidade: GE suites existentes + testes dbt.
- [ ] SLA: DAG `@daily`; freshness declarada via `dbt source freshness` (Épico 4).
- [x] Contrato versionado no git junto dos models.

### Idempotency Gate (Art. IV)
- [ ] Re-execução produz mesmo resultado (Épico 3.3 — teste explícito 2× build).
- [ ] `DROP TABLE` eliminado do caminho de carga regular.

## Complexity Tracking

| Gate | Status | Justificativa |
|------|--------|---------------|
| Simplicity (Art. VI) | ✅ Aprovado | dbt substitui DDL manual — menos código próprio |
| Intentional Abstraction (Art. VII) | ✅ Aprovado | Framework padrão de mercado, zero wrapper |
| Data Contract (Art. III) | ✅ Aprovado | Pendências são entregas dos Épicos 2 e 4 |
| Idempotency (Art. IV) | ✅ Aprovado | Objetivo central do Épico 3 |

## Critérios de Aceite

- [ ] `dbt build` verde local e no CI, com todos os testes dbt passando.
- [ ] Build 2× sobre mesmo raw → mesma contagem no fact (idempotência provada).
- [ ] DAG roda em máquina limpa (container) sem editar paths.
- [ ] `Dockerfile` presente; `docker build` passa no CI.
- [ ] GE suites verdes pós-transformação.
- [ ] Nenhum CSV de dado bruto versionado fora de `tests/fixtures/`.
- [ ] README atualizado: linhagem dbt (screenshot), seção incremental/idempotência, badge CI.
