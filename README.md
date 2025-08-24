# Projeto de Engenharia de Dados: Data Warehouse da OMS

## Objetivo do Projeto OMS

O objetivo principal deste projeto é executar uma tarefa completa de engenharia de dados, projetando e construindo um Data Warehouse robusto e escalável. Este Data Warehouse será populado com dados da API do Observatório de Saúde Global (GHO) da Organização Mundial da Saúde (OMS).

O produto final será um banco de dados bem estruturado, servindo como uma fonte única de verdade (`single source of truth`) para analistas e cientistas de dados, permitindo-lhes consultar e analisar tendências de saúde global de forma fácil e eficiente.

## Análise da API

A API GHO da OMS é uma API OData. Nossa análise inicial revelou as seguintes características:

*   **Endpoints de Dados:** A API expõe milhares de endpoints, onde a grande maioria corresponde a um `IndicatorCode` (código de indicador) individual.
*   **Endpoints Estruturais (Metadados):** Existem alguns endpoints chave que fornecem metadados sobre a estrutura da API:
    *   `Indicator`: Fornece a lista de todos os indicadores de saúde disponíveis.
    *   `DIMENSION`: Lista todas as dimensões possíveis para filtrar os dados (ex: País, Ano, Sexo).
    *   `Region`: Lista as regiões da OMS.

## Arquitetura do Banco de Dados Proposta: Star Schema

Para organizar os dados visando otimizar as consultas e análises, implementaremos um **Star Schema**. Esta é uma abordagem padrão da indústria para a construção de Data Warehouses.

### Tabela Fato (Central)

*   `fact_observations`
    *   `observation_id` (Chave Primária)
    *   `indicator_id` (Chave Estrangeira para `dim_indicators`)
    *   `location_id` (Chave Estrangeira para `dim_locations`)
    *   `period_id` (Chave Estrangeira para `dim_periods`)
    *   `value` (O valor numérico da observação)
    *   *... (outras chaves estrangeiras para mais dimensões)*

### Tabelas de Dimensão (Contexto)

*   `dim_indicators`
    *   `indicator_id` (Chave Primária)
    *   `indicator_code`
    *   `indicator_name`
    *   `category`
*   `dim_locations`
    *   `location_id` (Chave Primária)
    *   `country_name`
    *   `region_name`
*   `dim_periods`
    *   `period_id` (Chave Primária)
    *   `year`
*   Outras tabelas de dimensão conforme necessário (ex: `dim_sex`, `dim_age_group`).

## Orquestração

### Pipeline de Ingestão de Dados

O Data Warehouse é populado usando um pipeline de ingestão de dados baseado em Python com os seguintes passos:

1.  **Extração (Extract):** Scripts buscam os dados da API da OMS, incluindo metadados (indicadores, dimensões) e os dados observacionais.
2.  **Transformação (Transform):** Os dados brutos (JSON) da API são limpos, estruturados e transformados para se adequarem ao nosso modelo Star Schema.
3.  **Carga (Load):** Os dados transformados são carregados nas tabelas apropriadas em nosso Data Warehouse (inicialmente, um banco de dados SQLite local).

### Agendamento

Atualmente, o agendamento da execução do pipeline é feito utilizando o `cron` do sistema operacional.

**Exemplo de configuração no `crontab`:**

```cron
0 1 * * * /usr/bin/python3 /mnt/arquivos/Data\ Science/Engenheiro\ de\ Dados_Azure/projeto_oms/scripts/populate_database.py >> /mnt/arquivos/Data\ Science/Engenheiro\ de\ Dados_Azure/projeto_oms/cron_job.log 2>&1
```

No futuro, planejamos migrar para uma ferramenta de orquestração mais robusta, como o Apache Airflow, para um gerenciamento de fluxo de trabalho mais avançado, monitoramento e tratamento de erros.

## Status da Ingestão

Até o momento, as seguintes categorias de indicadores foram processadas e carregadas no Data Warehouse:

*   **NCD**: Doenças Não Transmissíveis (176 indicadores)
*   **AIR**: Poluição do Ar (39 indicadores)

O banco de dados agora contém um subconjunto rico de dados pronto para análise. O pipeline pode ser executado para outras categorias, conforme necessário.

## Estrutura do Projeto

*   `data/`: Arquivos de dados brutos e processados (ex: `indicators.csv`, `dimensions.json`, `data_quality_log.txt`).
*   `notebooks/`: Jupyter Notebooks para análise exploratória e testes.
*   `scripts/`: Scripts Python para o pipeline de ETL (Extração, Transformação e Carga).
*   `database/`: Conterá o arquivo do banco de dados SQLite.
*   `cron_job.log`: Log das execuções agendadas pelo `cron`.

## Gerenciamento do Banco de Dados Local

O arquivo `database/who_gho.db` contém o Data Warehouse SQLite local. Devido ao seu tamanho, ele **não é versionado diretamente no GitHub**.

**Para obter ou recriar o banco de dados:**

*   Você pode recriá-lo executando os scripts `scripts/create_database.py` (para criar o esquema) e `scripts/populate_database.py` (para popular com dados da API da OMS).
*   Alternativamente, para projetos maiores, o arquivo pode ser hospedado em serviços de armazenamento em nuvem (como Google Drive, Dropbox, etc.) e o link pode ser compartilhado.

**Representação da Estrutura do Banco de Dados:**

Para fornecer uma visão da estrutura do banco de dados sem incluir o arquivo completo, geramos um arquivo JSON:

*   `database/db_schema_summary.json`: Este arquivo contém um resumo do esquema do banco de dados, incluindo nomes de tabelas e colunas. Ele é gerado pelo script `scripts/create_db_schema_summary.py` e é versionado no GitHub.

## Habilidades Desenvolvidas

*   Engenharia de Dados
*   Modelagem de Dados (Star Schema)
*   Desenvolvimento de Pipelines de ETL
*   Qualidade de Dados e Tratamento de Erros
*   Python (Pandas, SQLAlchemy, Requests, Tenacity)
*   Integração de APIs
*   Data Warehousing
*   Orquestração (Cron, futuro Airflow)

## Qualidade de Dados com Great Expectations

Para garantir a integridade e a qualidade dos dados que entram em nosso Data Warehouse, utilizamos a ferramenta Great Expectations.

### Solução de Problemas na Configuração (Troubleshooting)

Durante a configuração inicial do Great Expectations, encontramos uma série de erros persistentes que impediam a conexão com a fonte de dados. A causa raiz foi identificada como uma incompatibilidade entre a configuração do conector de dados e a forma como os dados estavam sendo acessados pelo script Python.

*   **Problema**: Ao tentar validar dados de forma dinâmica em um script (passando o caminho de um arquivo CSV em tempo de execução), a biblioteca retornava erros como `ValueError: RuntimeBatchRequests must specify exactly one corresponding BatchDefinition`.
*   **Causa Raiz**: A configuração inicial no `great_expectations.yml` utilizava um `InferredAssetFilesystemDataConnector`, que é projetado para mapear arquivos de dados que já são conhecidos pelo sistema. No entanto, a validação dinâmica requer um `RuntimeDataConnector`.
*   **Solução**:
    1.  O arquivo `great_expectations.yml` foi ajustado para usar um `RuntimeDataConnector`.
    2.  O script de validação (`scripts/test_gx_connection.py`) foi modificado para construir um `RuntimeBatchRequest`, que passa explicitamente o caminho do arquivo a ser validado. Esta abordagem se alinha com a configuração do conector e resolveu o conflito.

O script `scripts/test_gx_connection.py` serve agora como um modelo funcional para criar novas suítes de expectativas para nossos arquivos de dados.

## Conceitos Avançados de Engenharia de Dados Demonstrados

Este projeto foi expandido para demonstrar a aplicação prática de diversos conceitos avançados de Engenharia de Dados, com foco em automação e melhores práticas utilizando Python. Para cada conceito, um script Python e um documento explicativo detalhado (`docs/`) foram criados.

*   **Orquestração de Pipeline (Apache Airflow):**
    *   **Conceito:** Automação e agendamento de fluxos de trabalho complexos de dados usando DAGs.
    *   **Demonstração:** Script Python (`dags/oms_data_pipeline.py`) que define uma DAG para orquestrar a ingestão e validação de dados.
*   **Conteinerização (Docker):**
    *   **Conceito:** Empacotamento de aplicações e seus ambientes em unidades portáteis e reprodutíveis.
    *   **Demonstração:** Script Python (`scripts/create_dockerfile.py`) que gera um `Dockerfile` para construir uma imagem Docker do projeto.
*   **Simulação de Data Lake:**
    *   **Conceito:** Armazenamento de dados brutos em um repositório centralizado para flexibilidade e escalabilidade.
    *   **Demonstração:** Script Python (`scripts/simulate_data_lake_ingestion.py`) que simula a ingestão de dados brutos da API para uma pasta local que atua como um Data Lake.
*   **Monitoramento e Logging Aprimorado:**
    *   **Conceito:** Registro detalhado de eventos para observabilidade, depuração e alertas em pipelines de dados.
    *   **Demonstração:** Implementação do módulo `logging` do Python no script de população do banco de dados (`scripts/populate_database.py`) para logs estruturados e direcionados a arquivo/console.
*   **Governança de Dados e Metadados (Docstrings e Type Hinting):**
    *   **Conceito:** Melhoria da clareza, manutenibilidade e documentação interna do código para facilitar o entendimento e a gestão dos dados.
    *   **Demonstração:** Adição de docstrings e type hints em funções e parâmetros no script de população do banco de dados (`scripts/populate_database.py`).