import pandas as pd
import sqlite3
import os
import requests

def get_db_connection():
    """Cria uma conexão com o banco de dados SQLite."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(script_dir, '..', 'database', 'who_gho.db')
    return sqlite3.connect(db_path)

def enrich_locations():
    """Enriquece a tabela dim_locations com nomes de países."""
    print("--- Enriquecendo a Tabela dim_locations ---")
    
    # URL para o arquivo CSV de códigos de país
    url = "https://datahub.io/core/country-codes/r/country-codes.csv"
    
    try:
        # Baixar o arquivo CSV
        print(f"Baixando dados de países de: {url}")
        response = requests.get(url)
        response.raise_for_status()  # Lança um erro para status HTTP ruins

        # Salvar o conteúdo em um arquivo temporário
        temp_csv_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'country_codes.csv')
        with open(temp_csv_path, 'w', encoding='utf-8') as f:
            f.write(response.text)
        
        # Ler o CSV em um DataFrame do pandas
        country_df = pd.read_csv(temp_csv_path)
        
        # Manter apenas as colunas necessárias e renomeá-las para clareza
        # O código da OMS corresponde ao ISO3166-1-Alpha-3
        country_df = country_df[['ISO3166-1-Alpha-3', 'official_name_en']]
        country_df.columns = ['country_code', 'country_name']

        # Criar um dicionário para mapeamento rápido
        country_map = country_df.set_index('country_code')['country_name'].to_dict()

        # Conectar ao banco de dados
        conn = get_db_connection()
        cursor = conn.cursor()

        # Buscar todos os códigos de país da dim_locations
        cursor.execute("SELECT location_id, country_code FROM dim_locations WHERE country_name IS NULL OR country_name = ''")
        locations_to_update = cursor.fetchall()
        
        print(f"Encontrados {len(locations_to_update)} locais para enriquecer.")

        updated_count = 0
        # Atualizar cada linha com o nome do país correspondente
        for location_id, country_code in locations_to_update:
            country_name = country_map.get(country_code)
            if country_name:
                cursor.execute("UPDATE dim_locations SET country_name = ? WHERE location_id = ?", (country_name, location_id))
                updated_count += 1

        conn.commit()
        print(f"{updated_count} nomes de países foram atualizados com sucesso.")

    except requests.exceptions.RequestException as e:
        print(f"Erro ao baixar o arquivo de países: {e}")
    except Exception as e:
        print(f"Ocorreu um erro: {e}")
    finally:
        # Limpar o arquivo temporário
        if os.path.exists(temp_csv_path):
            os.remove(temp_csv_path)
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == "__main__":
    enrich_locations()
