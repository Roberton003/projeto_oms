# 04 - Monitoramento e Alertas: Logging Aprimorado

Este documento explica a importância do logging em pipelines de dados e como implementar um logging aprimorado usando o módulo `logging` do Python.

## Conceito de Logging para Monitoramento

Logging é o processo de registrar eventos que ocorrem em um software. Em pipelines de dados, o logging é crucial para:
*   **Monitoramento:** Acompanhar o progresso das tarefas e identificar gargalos.
*   **Depuração:** Rastrear a causa de erros e falhas.
*   **Auditoria:** Manter um registro das operações realizadas.
*   **Alertas:** Disparar notificações quando eventos críticos (como erros) ocorrem.

O módulo `logging` do Python oferece uma maneira flexível de registrar mensagens em diferentes níveis de severidade (DEBUG, INFO, WARNING, ERROR, CRITICAL) e direcioná-las para vários destinos (console, arquivo, rede).

## Script com Logging Aprimorado

Vamos aprimorar o script `scripts/populate_database.py` para incluir logging detalhado. Isso permitirá um melhor monitoramento da ingestão de dados.

**Localização do Script:** `scripts/populate_database.py`

```python
import sqlite3
import pandas as pd
import os
import requests
import traceback
import logging # Importa o módulo logging

# Configuração básica do logger
logging.basicConfig(
    level=logging.INFO, # Define o nível mínimo de mensagens a serem registradas
    format='%(asctime)s - %(levelname)s - %(message)s', # Formato da mensagem
    handlers=[
        logging.FileHandler("populate_database.log"), # Salva logs em arquivo
        logging.StreamHandler() # Exibe logs no console
    ]
)

def get_db_connection():
    """Cria uma conexão com o banco de dados SQLite."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(script_dir, '..', 'database', 'who_gho.db')
    logging.info(f"Conectando ao banco de dados em: {db_path}")
    return sqlite3.connect(db_path)

def populate_dimensions():
    """Popula as tabelas de dimensão no banco de dados SQLite."""
    logging.info("--- Iniciando População das Tabelas de Dimensão ---")
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Popula dim_indicators
        indicators_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'categorized_indicators.csv')
        logging.info(f"Lendo indicadores de: {indicators_path}")
        indicators_df = pd.read_csv(indicators_path)
        indicators_df.to_sql('dim_indicators_temp', conn, if_exists='replace', index=False)
        cursor.execute("""
            INSERT OR IGNORE INTO dim_indicators (indicator_code, indicator_name, category)
            SELECT IndicatorCode, IndicatorName, Category FROM dim_indicators_temp
        """)
        cursor.execute("DROP TABLE dim_indicators_temp")
        logging.info(f"{cursor.rowcount} novos indicadores processados.")

        # Popula dim_sex
        sex_data = [('MLE', 'Male'), ('FMLE', 'Female'), ('BTSX', 'Both sexes')]
        cursor.executemany("INSERT OR IGNORE INTO dim_sex (sex_code, sex_name) VALUES (?, ?)", sex_data)
        logging.info("Dimensão de sexo populada.")

        conn.commit()
        logging.info("Tabelas de dimensão populadas com sucesso.")

    except Exception as e:
        logging.error(f"Ocorreu um erro durante a população das dimensões: {e}", exc_info=True)
        conn.rollback()
    finally:
        conn.close()
        logging.info("Conexão com o banco de dados fechada.")

def get_or_create_id(cursor, table, id_column, code_column, code_value):
    """Obtém o ID de um valor em uma tabela de dimensão, criando-o se não existir."""
    sql_select = f"SELECT {id_column} FROM {table} WHERE {code_column} = ?"
    cursor.execute(sql_select, (code_value,))
    result = cursor.fetchone()
    if result:
        return result[0]
    else:
        sql_insert = f"INSERT INTO {table} ({code_column}) VALUES (?)"
        cursor.execute(sql_insert, (code_value,))
        return cursor.lastrowid

def populate_facts(category='NCD'):
    """Busca dados para uma dada categoria e popula a tabela fact_observations."""
    logging.info(f"--- Iniciando População da Tabela de Fatos para a Categoria: {category} ---")
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT indicator_id, indicator_code FROM dim_indicators WHERE category = ?", (category,))
        indicators = cursor.fetchall()
        logging.info(f"Encontrados {len(indicators)} indicadores para a categoria '{category}'.")

        for indicator_id, indicator_code in indicators:
            logging.info(f"Buscando dados para o indicador: {indicator_code}...")
            response = requests.get(f"https://ghoapi.azureedge.net/api/{indicator_code}", timeout=30)
            response.raise_for_status() # Lança um erro para status HTTP ruins
            
            if response.status_code == 200 and 'value' in response.json():
                observations = response.json()['value']
                logging.info(f"  -> {len(observations)} observações encontradas para {indicator_code}.")
                for obs in observations:
                    if all(k in obs for k in ['SpatialDim', 'TimeDim']) and obs.get('NumericValue') is not None:
                        country_code = obs['SpatialDim']
                        year = obs['TimeDim']
                        
                        sex_code = obs.get('Dim1') # Dim1 is often SEX
                        sex_id = None
                        if sex_code:
                            # Clean the code
                            if sex_code.startswith('SEX_'):
                                sex_code = sex_code.replace('SEX_', '')
                            
                            # Check if it's a valid sex code before processing
                            if sex_code in ['MLE', 'FMLE', 'BTSX']:
                                sex_id = get_or_create_id(cursor, 'dim_sex', 'sex_id', 'sex_code', sex_code)

                        value = obs.get('NumericValue')

                        location_id = get_or_create_id(cursor, 'dim_locations', 'location_id', 'country_code', country_code)
                        period_id = get_or_create_id(cursor, 'dim_periods', 'period_id', 'year', year)
                        
                        sql_insert_fact = """
                            INSERT INTO fact_observations (indicator_id, location_id, period_id, sex_id, value)
                            VALUES (?, ?, ?, ?, ?)
                        """
                        cursor.execute(sql_insert_fact, (indicator_id, location_id, period_id, sex_id, value))
            else:
                logging.warning(f"  -> Sem dados ou erro para o indicador: {indicator_code}")

        conn.commit()
        logging.info(f"Tabela de fatos populada com sucesso para a categoria '{category}'.")

    except requests.exceptions.RequestException as e:
        logging.error(f"Erro de requisição ao buscar dados para a categoria {category}: {e}", exc_info=True)
        conn.rollback()
    except Exception as e:
        logging.error(f"Ocorreu um erro inesperado durante a população de fatos para a categoria {category}: {e}", exc_info=True)
        conn.rollback()
    finally:
        conn.close()
        logging.info("Conexão com o banco de dados fechada.")

if __name__ == "__main__":
    populate_dimensions()
    populate_facts('AIR')
```

## Entendimento e Propósito do Script

Este script demonstra a implementação de logging robusto em um pipeline de dados.

*   **`import logging`**: Importa o módulo de logging do Python.
*   **`logging.basicConfig(...)`**: Configura o logger básico para:
    *   `level=logging.INFO`: Mensagens de nível INFO e superiores serão registradas.
    *   `format`: Define o formato das mensagens de log (timestamp, nível, mensagem).
    *   `handlers`: Direciona as mensagens para um arquivo (`populate_database.log`) e para o console.
*   **`logging.info(...)`, `logging.warning(...)`, `logging.error(...)`**: Substituem os `print()` para registrar eventos com níveis de severidade apropriados.
*   **`exc_info=True`**: Usado em `logging.error` para incluir informações completas da exceção (stack trace) no log, o que é crucial para depuração.
*   **`conn.rollback()`**: Adicionado em blocos `except` para garantir que as transações sejam desfeitas em caso de erro, mantendo a integridade do banco de dados.

**Significado para o Projeto:**

O logging aprimorado é fundamental para a observabilidade de pipelines de dados. Ele permite:
*   **Rastreabilidade:** Saber exatamente o que aconteceu em cada etapa da execução.
*   **Depuração Eficaz:** Identificar rapidamente a causa de falhas com informações detalhadas.
*   **Monitoramento Proativo:** Em um ambiente de produção, esses logs podem ser coletados por ferramentas de monitoramento para disparar alertas em caso de problemas.

## Como Executar

1.  **Executar o script:**
    ```bash
    venv/bin/python scripts/populate_database.py
    ```
    Este comando executará o pipeline de ingestão de dados.

2.  **Verificar os logs:**
    ```bash
    cat populate_database.log
    ```
    Você verá as mensagens de log detalhadas no console e no arquivo `populate_database.log` na raiz do projeto.
