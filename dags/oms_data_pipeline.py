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
        bash_command='venv/bin/python /mnt/arquivos/Data Science/Engenheiro de Dados_Azure/projeto_oms/scripts/populate_database.py',
    )

    # Task para executar o script de validação do Great Expectations para indicators.csv
    validate_indicators_task = BashOperator(
        task_id='validate_indicators_data',
        bash_command='venv/bin/python /mnt/arquivos/Data Science/Engenheiro de Dados_Azure/projeto_oms/scripts/test_gx_connection.py',
    )

    # Task para executar o script de validação do Great Expectations para categorized_indicators.csv
    validate_categorized_indicators_task = BashOperator(
        task_id='validate_categorized_indicators_data',
        bash_command='venv/bin/python /mnt/arquivos/Data Science/Engenheiro de Dados_Azure/projeto_oms/scripts/validate_categorized_indicators.py',
    )

    # Task para executar o script de validação do Great Expectations para dimensions.json
    validate_dimensions_task = BashOperator(
        task_id='validate_dimensions_data',
        bash_command='venv/bin/python /mnt/arquivos/Data Science/Engenheiro de Dados_Azure/projeto_oms/scripts/validate_dimensions.py',
    )

    # Define as dependências das tasks
    # A população do banco de dados deve ocorrer antes da validação
    populate_db_task >> [
        validate_indicators_task,
        validate_categorized_indicators_task,
        validate_dimensions_task
    ]
