import requests
import os
import json
from datetime import datetime

# URL base da API da OMS
BASE_URL = "https://ghoapi.azureedge.net/api/"

# Define o diretório do Data Lake (local)
data_lake_raw_dir = os.path.join('data_lake', 'raw')
os.makedirs(data_lake_raw_dir, exist_ok=True)

def ingest_raw_data_to_data_lake(endpoint: str, filename_prefix: str):
    """Simula a ingestão de dados brutos da API da OMS para um Data Lake local."""
    url = f"{BASE_URL}{endpoint}"
    print(f"Tentando ingerir dados brutos de: {url}")

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()  # Lança um erro para status HTTP ruins

        # Gera um nome de arquivo com timestamp para evitar sobrescrever
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"{filename_prefix}_{timestamp}.json"
        output_path = os.path.join(data_lake_raw_dir, output_filename)

        # Salva a resposta JSON bruta no 'Data Lake' local
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(response.json(), f, indent=4)
        
        print(f"Dados brutos de '{endpoint}' salvos em: {output_path}")
        print("Em um cenário real, isso seria o upload para um bucket S3, Azure Blob Storage, etc.")

    except requests.exceptions.RequestException as e:
        print(f"Erro ao ingerir dados brutos de {endpoint}: {e}")
    except Exception as e:
        print(f"Ocorreu um erro inesperado: {e}")

if __name__ == "__main__":
    # Exemplo de uso: Ingerir dados de Indicadores
    ingest_raw_data_to_data_lake("Indicator", "indicators_raw")
    
    # Exemplo de uso: Ingerir dados de uma categoria específica (se disponível e funcional)
    # ingest_raw_data_to_data_lake("NCD", "ncd_category_raw")
    
    # Exemplo de uso: Ingerir dados de Dimensões
    ingest_raw_data_to_data_lake("DIMENSION", "dimensions_raw")

    # Exemplo de uso: Ingerir dados de Regiões (sabemos que está quebrado, mas para demonstração)
    # ingest_raw_data_to_data_lake("Region", "regions_raw")
