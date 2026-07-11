# WHO Global Health Observatory — Star Schema Analytics

Pipeline analítico sobre dados públicos de saúde global da **Organização Mundial da Saúde (WHO GHO API)**, modelado em Star Schema com **dbt + DuckDB**.

---

## Arquitetura

```
┌──────────────────┐     ┌─────────────────┐     ┌──────────────────────┐
│  WHO GHO API     │────▶│  SQLite (raw)    │────▶│  dbt + DuckDB        │
│  (OData JSON)    │     │  who_gho.db      │     │  Star Schema (marts) │
└──────────────────┘     └─────────────────┘     ├──────────────────────┤
                                                  │ dim_indicator        │
                                                  │ dim_location         │
                                                  │ dim_period           │
                                                  │ dim_sex              │
                                                  │ fct_observations     │
                                                  └──────────────────────┘
                                                           │
                                                           ▼
                                                  ┌──────────────────┐
                                                  │  Testes dbt      │
                                                  │  32 testes       │
                                                  │  (unique, not    │
                                                  │   null, rel.,    │
                                                  │   accepted val.) │
                                                  └──────────────────┘
```

### Fluxo

1. **Ingestão**: Scripts Python consomem a API OData da OMS e populam um banco SQLite raw (`database/who_gho.db`)
2. **Transformação (dbt)**: dbt-core com adaptador DuckDB lê o SQLite via extensão `sqlite_scanner` e constrói o Star Schema
3. **Testes**: 32 testes de dados (unique, not_null, relationships, accepted_values) garantem integridade
4. **Incremental**: `fct_observations` usa materialização incremental (merge por `observation_id`)

---

## Stack

| Camada | Tecnologia |
|--------|-----------|
| Transformação | [dbt-core](https://github.com/dbt-labs/dbt-core) 1.11 + [dbt-duckdb](https://github.com/duckdb/dbt-duckdb) 1.10 |
| Query Engine | [DuckDB](https://duckdb.org/) (OLAP embarcado) |
| Raw Storage | SQLite (fonte original) |
| Orquestração | Apache Airflow (opcional) |
| CI/CD | GitHub Actions |
| Container | Docker (Python 3.12-slim) |

---

## Modelagem Dimensional (Kimball Star Schema)

### Tabela Fato

**`fct_observations`** — grão por observação individual

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `observation_id` | int | PK natural da fonte |
| `observation_key` | varchar | Surrogate key (hash) |
| `indicator_id` | int | FK → `dim_indicator` |
| `location_id` | int | FK → `dim_location` |
| `period_id` | int | FK → `dim_period` |
| `sex_id` | int | FK → `dim_sex` (0 = UNK) |
| `value` | float | Valor numérico da observação |

### Dimensões

| Tabela | Descrição | Cardinalidade |
|--------|-----------|--------------|
| `dim_indicator` | Indicadores de saúde (código, nome, categoria) | ~3K |
| `dim_location` | Países/regiões (código ISO, nome, região) | ~220 |
| `dim_period` | Períodos (ano, agrupamento por década) | ~70 |
| `dim_sex` | Sexo (MLE, FMLE, BTSX, UNK) | 4 |

---

## Como Executar

### Setup rápido

```bash
# 1. Clonar
git clone https://github.com/Roberton003/projeto_oms.git
cd projeto_oms

# 2. Setup completo
make setup

# 3. Build (modelos + testes)
make build

# 4. Apenas testes
make test
```

### Targets disponíveis

| Comando | Descrição |
|---------|-----------|
| `make setup` | Cria virtualenv + instala dependências + pacotes dbt |
| `make build` | Executa `dbt build` (modelos + testes) |
| `make test` | Executa `dbt test` (apenas testes) |
| `make run` | Executa `dbt run` (apenas modelos) |
| `make ci` | CI completo (banco de teste + clean + build) |
| `make clean` | Limpa artefatos dbt e banco DuckDB |
| `make shell` | Abre DuckDB shell no banco do target atual |

### CI/CD

```bash
make ci
```

O target `ci` cria um banco SQLite sintético (10 observações), limpa artefatos anteriores e executa `dbt build --target ci`. O mesmo fluxo roda no GitHub Actions a cada push.

### Docker

```bash
docker build -t projeto-oms .
docker run --rm projeto-oms make ci
```

---

## Obtenção dos Dados

Os dados são obtidos da API OData do WHO GHO:

```bash
# Listar indicadores disponíveis
python scripts/coleta_oms.py

# Pipeline completo de ingestão
python scripts/populate_database.py
```

O script `populate_database.py` consome a API da OMS por indicador e popula o banco SQLite `database/who_gho.db`, que é então lido pelo dbt.

> **Fixtures de teste**: `tests/fixtures/` contém snapshots dos dados da API para CI/CD.
> Dados brutos não são versionados — execute os scripts de ingestão para obtê-los.

---

## Qualidade de Dados

- **32 testes dbt**: unique, not_null, relationships, accepted_values
- **Great Expectations** (opcional): suítes de validação complementares em `scripts/`
- **Incremental idempotente**: `fct_observations` com merge por `observation_id`

---

## Licença

Dados: [WHO GHO](https://www.who.int/data/gho) — uso livre com atribuição.
Código: MIT.
