# 01 - Orquestração de Pipeline de Dados com Apache Airflow

Este documento explica como o Apache Airflow pode ser utilizado para orquestrar o pipeline de ingestão e validação de dados do projeto OMS.

## Conceito de Orquestração com Airflow

A orquestração de dados é o processo de automatizar, agendar e monitorar fluxos de trabalho complexos de dados. O Apache Airflow é uma plataforma líder para essa finalidade, permitindo definir pipelines como DAGs (Directed Acyclic Graphs) em código Python.

**Benefícios:**
*   **Automação:** Agendamento automático de tarefas.
*   **Monitoramento:** Interface web para acompanhar o status das execuções.
*   **Resiliência:** Retentativas automáticas e tratamento de falhas.
*   **Visualização:** Representação gráfica do fluxo de trabalho.

## Script da DAG (Directed Acyclic Graph)

A DAG é o coração da orquestração no Airflow. Ela define as tarefas (tasks) e suas dependências.

**Localização do Script:** `dags/oms_data_pipeline.py`

```python
from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime

with DAG(
    dag_id='oms_data_pipeline',
    start_date=datetime(2023, 1, 1),
    schedule_interval='@daily',
    catchup=False,
    tags=['oms', 'data_ingestion'],
) as dag:
    # Task para executar o script populate_database.py
    # Este script lida com a população das tabelas de dimensão e fato
    populate_db_task = BashOperator(
        task_id='populate_database',
        bash_command='venv/bin/python /mnt/arquivos/Data\ Science/Engenheiro\ de\ Dados_Azure/projeto_oms/scripts/populate_database.py',
    )

    # Task para executar o script de validação do Great Expectations para indicators.csv
    validate_indicators_task = BashOperator(
        task_id='validate_indicators_data',
        bash_command='venv/bin/python /mnt/arquivos/Data\ Science/Engenheiro\ de\ Dados_Azure/projeto_oms/scripts/test_gx_connection.py',
    )

    # Task para executar o script de validação do Great Expectations para categorized_indicators.csv
    validate_categorized_indicators_task = BashOperator(
        task_id='validate_categorized_indicators_data',
        bash_command='venv/bin/python /mnt/arquivos/Data\ Science/Engenheiro\ de\ Dados_Azure/projeto_oms/scripts/validate_categorized_indicators.py',
    )

    # Task para executar o script de validação do Great Expectations para dimensions.json
    validate_dimensions_task = BashOperator(
        task_id='validate_dimensions_data',
        bash_command='venv/bin/python /mnt/arquivos/Data\ Science/Engenheiro\ de\ Dados_Azure/projeto_oms/scripts/validate_dimensions.py',
    )

    # Define as dependências das tasks
    # A população do banco de dados deve ocorrer antes da validação
    populate_db_task >> [
        validate_indicators_task,
        validate_categorized_indicators_task,
        validate_dimensions_task
    ]
```

## Entendimento e Propósito do Script

Este script Python define a lógica de orquestração para o Airflow. Ele não executa o pipeline diretamente, mas sim descreve como o Airflow deve executá-lo.

*   **`DAG`**: O objeto `DAG` encapsula todo o fluxo de trabalho.
*   **`start_date` e `schedule_interval`**: Definem quando a DAG deve começar a ser executada e com que frequência.
*   **`BashOperator`**: É usado para executar comandos de shell. Neste caso, ele invoca os scripts Python existentes do projeto.
*   **`>>` (Bitshift Operator):** Define as dependências entre as tarefas. A tarefa à esquerda deve ser concluída com sucesso antes que as tarefas à direita possam começar.

**Significado para o Projeto:**

Este script demonstra a capacidade de transformar um conjunto de scripts independentes em um pipeline de dados automatizado e gerenciável. Em um ambiente de produção, o Airflow seria responsável por garantir que os dados sejam ingeridos e validados diariamente (ou na frequência desejada), com monitoramento centralizado e tratamento de erros.

## Como Executar (Conceitual)

Para executar esta DAG, você precisaria ter uma instalação funcional do Apache Airflow.

1.  **Instalar Airflow:** `pip install apache-airflow` (e configurar um banco de dados de metadados).
2.  **Colocar a DAG:** Copie o arquivo `oms_data_pipeline.py` para o diretório `dags/` configurado na sua instalação do Airflow.
3.  **Ativar e Monitorar:** Acesse a interface web do Airflow, ative a DAG `oms_data_pipeline` e monitore suas execuções.

Este script é a "receita" para o Airflow executar seu pipeline.
