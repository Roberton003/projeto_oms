import sqlite3
import pandas as pd
import os
import requests
import traceback

def get_db_connection():
    """Creates a connection to the SQLite database."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(script_dir, '..', 'database', 'who_gho.db')
    return sqlite3.connect(db_path)

def populate_dimensions():
    """Populates the dimension tables in the SQLite database."""
    print("--- Populating Dimension Tables ---")
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Populate dim_indicators
        indicators_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'categorized_indicators.csv')
        indicators_df = pd.read_csv(indicators_path)
        indicators_df.to_sql('dim_indicators_temp', conn, if_exists='replace', index=False)
        cursor.execute("""
            INSERT OR IGNORE INTO dim_indicators (indicator_code, indicator_name, category)
            SELECT IndicatorCode, IndicatorName, Category FROM dim_indicators_temp
        """)
        cursor.execute("DROP TABLE dim_indicators_temp")
        print(f"{cursor.rowcount} new indicators processed.")

        # Populate dim_sex
        sex_data = [('MLE', 'Male'), ('FMLE', 'Female'), ('BTSX', 'Both sexes')]
        cursor.executemany("INSERT OR IGNORE INTO dim_sex (sex_code, sex_name) VALUES (?, ?)", sex_data)
        print("Sex dimension populated.")

        conn.commit()
        import sqlite3
import pandas as pd
import os
import requests
import traceback
import logging # Importa o módulo logging
from typing import List, Tuple, Dict, Any, Optional # Importa tipos para type hinting

# Configuração básica do logger
logging.basicConfig(
    level=logging.INFO, # Define o nível mínimo de mensagens a serem registradas
    format='%(asctime)s - %(levelname)s - %(message)s', # Formato da mensagem
    handlers=[
        logging.FileHandler("populate_database.log"), # Salva logs em arquivo
        logging.StreamHandler() # Exibe logs no console
    ]
)

def get_db_connection() -> sqlite3.Connection:
    """Cria e retorna uma conexão com o banco de dados SQLite.

    Retorna:
        sqlite3.Connection: Objeto de conexão com o banco de dados.
    """
    script_dir: str = os.path.dirname(os.path.abspath(__file__))
    db_path: str = os.path.join(script_dir, '..', 'database', 'who_gho.db')
    logging.info(f"Conectando ao banco de dados em: {db_path}")
    return sqlite3.connect(db_path)

def populate_dimensions() -> None:
    """Popula as tabelas de dimensão (dim_indicators, dim_sex) no banco de dados SQLite.

    Este processo inclui a leitura de indicadores de um CSV e a inserção de dados de sexo pré-definidos.
    """
    logging.info("--- Iniciando População das Tabelas de Dimensão ---")
    conn: Optional[sqlite3.Connection] = None
    try:
        conn = get_db_connection()
        cursor: sqlite3.Cursor = conn.cursor()

        # Popula dim_indicators
        indicators_path: str = os.path.join(os.path.dirname(__file__), '..', 'data', 'categorized_indicators.csv')
        logging.info(f"Lendo indicadores de: {indicators_path}")
        indicators_df: pd.DataFrame = pd.read_csv(indicators_path)
        indicators_df.to_sql('dim_indicators_temp', conn, if_exists='replace', index=False)
        cursor.execute("""
            INSERT OR IGNORE INTO dim_indicators (indicator_code, indicator_name, category)
            SELECT IndicatorCode, IndicatorName, Category FROM dim_indicators_temp
        """)
        cursor.execute("DROP TABLE dim_indicators_temp")
        logging.info(f"{cursor.rowcount} novos indicadores processados.")

        # Popula dim_sex
        sex_data: List[Tuple[str, str]] = [('MLE', 'Male'), ('FMLE', 'Female'), ('BTSX', 'Both sexes')]
        cursor.executemany("INSERT OR IGNORE INTO dim_sex (sex_code, sex_name) VALUES (?, ?)", sex_data)
        logging.info("Dimensão de sexo populada.")

        conn.commit()
        logging.info("Tabelas de dimensão populadas com sucesso.")

    except Exception as e:
        logging.error(f"Ocorreu um erro durante a população das dimensões: {e}", exc_info=True)
        if conn: conn.rollback()
    finally:
        if conn: 
            conn.close()
            logging.info("Conexão com o banco de dados fechada.")

def get_or_create_id(cursor: sqlite3.Cursor, table: str, id_column: str, code_column: str, code_value: str) -> int:
    """Obtém o ID de um valor em uma tabela de dimensão, criando-o se não existir.

    Args:
        cursor (sqlite3.Cursor): Cursor do banco de dados.
        table (str): Nome da tabela de dimensão.
        id_column (str): Nome da coluna de ID na tabela de dimensão.
        code_column (str): Nome da coluna de código na tabela de dimensão.
        code_value (str): Valor do código a ser buscado ou criado.

    Retorna:
        int: O ID do valor na tabela de dimensão.
    """
    sql_select: str = f"SELECT {id_column} FROM {table} WHERE {code_column} = ?"
    cursor.execute(sql_select, (code_value,))
    result: Optional[Tuple[int]] = cursor.fetchone()
    if result:
        return result[0]
    else:
        sql_insert: str = f"INSERT INTO {table} ({code_column}) VALUES (?)"
        cursor.execute(sql_insert, (code_value,))
        return cursor.lastrowid # type: ignore

def populate_facts(category: str = 'NCD') -> None:
    """Busca dados da API da OMS para uma dada categoria e popula a tabela fact_observations.

    Args:
        category (str): A categoria de indicadores a ser buscada (ex: 'NCD', 'AIR').
    """
    logging.info(f"--- Iniciando População da Tabela de Fatos para a Categoria: {category} ---")
    conn: Optional[sqlite3.Connection] = None
    try:
        conn = get_db_connection()
        cursor: sqlite3.Cursor = conn.cursor()

        cursor.execute("SELECT indicator_id, indicator_code FROM dim_indicators WHERE category = ?", (category,))
        indicators: List[Tuple[int, str]] = cursor.fetchall()
        logging.info(f"Encontrados {len(indicators)} indicadores para a categoria '{category}'.")

        for indicator_id, indicator_code in indicators:
            logging.info(f"Buscando dados para o indicador: {indicator_code}...")
            response: requests.Response = requests.get(f"https://ghoapi.azureedge.net/api/{indicator_code}", timeout=30)
            response.raise_for_status() # Lança um erro para status HTTP ruins
            
            if response.status_code == 200 and 'value' in response.json():
                observations: List[Dict[str, Any]] = response.json()['value']
                logging.info(f"  -> {len(observations)} observações encontradas para {indicator_code}.")
                for obs in observations:
                    if all(k in obs for k in ['SpatialDim', 'TimeDim']) and obs.get('NumericValue') is not None:
                        country_code: str = obs['SpatialDim']
                        year: int = obs['TimeDim']
                        
                        sex_code: Optional[str] = obs.get('Dim1') # Dim1 is often SEX
                        sex_id: Optional[int] = None
                        if sex_code:
                            # Clean the code
                            if sex_code.startswith('SEX_'):
                                sex_code = sex_code.replace('SEX_', '')
                            
                            # Check if it's a valid sex code before processing
                            if sex_code in ['MLE', 'FMLE', 'BTSX']:
                                sex_id = get_or_create_id(cursor, 'dim_sex', 'sex_id', 'sex_code', sex_code)

                        value: float = obs.get('NumericValue') # type: ignore

                        location_id: int = get_or_create_id(cursor, 'dim_locations', 'location_id', 'country_code', country_code)
                        period_id: int = get_or_create_id(cursor, 'dim_periods', 'period_id', 'year', year)
                        
                        sql_insert_fact: str = """
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
        if conn: conn.rollback()
    except Exception as e:
        logging.error(f"Ocorreu um erro inesperado durante a população de fatos para a categoria {category}: {e}", exc_info=True)
        if conn: conn.rollback()
    finally:
        if conn: 
            conn.close()
            logging.info("Conexão com o banco de dados fechada.")

if __name__ == "__main__":
    populate_dimensions()
    populate_facts('AIR')


    except Exception as e:
        print(f"An error occurred during dimension population: {e}")
        traceback.print_exc()
    finally:
        conn.close()

def get_or_create_id(cursor, table, id_column, code_column, code_value):
    """Gets the ID of a value in a dimension table, creating it if it doesn't exist."""
    sql_select = f"SELECT {id_column} FROM {table} WHERE {code_column} = ?"
    # print(f"Executing SELECT: {sql_select} with value: {code_value}")
    cursor.execute(sql_select, (code_value,))
    result = cursor.fetchone()
    if result:
        return result[0]
    else:
        sql_insert = f"INSERT INTO {table} ({code_column}) VALUES (?)"
        # print(f"Executing INSERT: {sql_insert} with value: {code_value}")
        cursor.execute(sql_insert, (code_value,))
        return cursor.lastrowid

def populate_facts(category='NCD'):
    """Fetches data for a given category and populates the fact_observations table."""
    print(f"--- Populating Fact Table for Category: {category} ---")
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT indicator_id, indicator_code FROM dim_indicators WHERE category = ?", (category,))
        indicators = cursor.fetchall()
        print(f"Found {len(indicators)} indicators for category '{category}'.")

        for indicator_id, indicator_code in indicators:
            print(f"Fetching data for indicator: {indicator_code}...")
            response = requests.get(f"https://ghoapi.azureedge.net/api/{indicator_code}")
            
            if response.status_code == 200 and 'value' in response.json():
                observations = response.json()['value']
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

                        sql_insert_fact = """
                            INSERT INTO fact_observations (indicator_id, location_id, period_id, sex_id, value)
                            VALUES (?, ?, ?, ?, ?)
                        """
                        # print(f"Executing INSERT into fact_observations with values: ({indicator_id}, {location_id}, {period_id}, {sex_id}, {value})")
                        cursor.execute(sql_insert_fact, (indicator_id, location_id, period_id, sex_id, value))
            else:
                print(f"  -> No data or error for indicator: {indicator_code}")

        conn.commit()
        print(f"\nFact table populated successfully for category '{category}'.")

    except Exception as e:
        print(f"An error occurred during fact population: {e}")
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == "__main__":
    populate_dimensions()
    populate_facts('AIR')
