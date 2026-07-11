"""
DAG Apache Airflow — WHO GHO → dbt Star Schema

Orquestra a execução do pipeline dbt com DuckDB, incluindo:
1. Check/init do banco SQLite raw
2. dbt build (modelos + testes)
3. Health check pós-execução

Instalação:
    pip install apache-airflow
    export AIRFLOW_HOME=$(pwd)/airflow
    mkdir -p $AIRFLOW_HOME/dags
    ln -s $(pwd)/dags/oms_data_pipeline.py $AIRFLOW_HOME/dags/
"""

import json
import logging
import os
import subprocess
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

logger = logging.getLogger(__name__)

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DBT_DIR = os.path.join(PROJECT_DIR, "dbt")
SCRIPTS_DIR = os.path.join(PROJECT_DIR, "scripts")
RAW_DB = os.path.join(PROJECT_DIR, "database", "who_gho.db")

default_args = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

dag = DAG(
    "oms_data_pipeline",
    default_args=default_args,
    description="WHO GHO → dbt Star Schema (batch diário)",
    schedule=timedelta(days=1),
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["oms", "dbt", "duckdb", "who"],
    doc_md=__doc__,
)


def _check_raw_db():
    """Verifica se o banco SQLite raw existe; inicializa se necessário."""
    if not os.path.isfile(RAW_DB):
        logger.warning("Raw DB not found at %s — initializing test DB", RAW_DB)
        subprocess.run(
            ["python3", "scripts/init_test_db.py"],
            cwd=PROJECT_DIR,
            check=True,
        )
    else:
        size_mb = os.path.getsize(RAW_DB) / (1024 * 1024)
        logger.info("Raw DB found: %s (%.1f MB)", RAW_DB, size_mb)


def _health_check():
    """Executa health check e salva resultado."""
    result = subprocess.run(
        ["python3", "scripts/health_check.py", "--json"],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        report = json.loads(result.stdout)
        logger.info("Health check: %s", json.dumps(report, indent=2))
    else:
        logger.error("Health check failed: %s", result.stderr)


check_raw_db = PythonOperator(
    task_id="check_raw_db",
    python_callable=_check_raw_db,
    dag=dag,
)

dbt_build = BashOperator(
    task_id="dbt_build",
    bash_command=f"cd {DBT_DIR} && dbt build --target {{{{ params.target | default('dev') }}}}",
    params={"target": os.environ.get("DBT_TARGET", "dev")},
    env={
        **os.environ,
        "DBT_RAW_DB": RAW_DB,
        "DBT_PROFILES_DIR": DBT_DIR,
    },
    dag=dag,
)

health_check = PythonOperator(
    task_id="health_check",
    python_callable=_health_check,
    dag=dag,
)

check_raw_db >> dbt_build >> health_check
