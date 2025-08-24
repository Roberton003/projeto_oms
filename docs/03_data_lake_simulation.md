# 03 - Simulação de Ingestão em Data Lake

Este documento explica o conceito de Data Lake e como a ingestão de dados brutos pode ser simulada em um ambiente local.

## Conceito de Data Lake

Um Data Lake é um repositório centralizado que permite armazenar todos os seus dados em qualquer escala. Você pode armazenar seus dados como eles são, sem precisar estruturá-los primeiro, e executar diferentes tipos de análises neles. Em Engenharia de Dados, é o local onde os dados brutos são primeiramente armazenados antes de serem processados e transformados para uso em Data Warehouses ou outras aplicações.

**Benefícios:**
*   **Armazenamento de Dados Brutos:** Permite armazenar todos os dados em seu formato original, sem perdas, para futuras análises ou reprocessamentos.
*   **Flexibilidade:** Não exige um esquema pré-definido, o que é ideal para dados não estruturados ou semi-estruturados.
*   **Escalabilidade:** Projetado para lidar com grandes volumes de dados.

## Script de Simulação de Ingestão em Data Lake

Este script simula a coleta de dados brutos da API da OMS e o armazenamento desses dados em uma pasta local que representa um "Data Lake".

**Localização do Script:** `scripts/simulate_data_lake_ingestion.py`

```python
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
```

## Entendimento e Propósito do Script

Este script Python demonstra o conceito de ingestão de dados brutos em um Data Lake.

*   **`data_lake/raw/`**: Uma pasta local que simula o armazenamento de dados brutos.
*   **`ingest_raw_data_to_data_lake`**: Função que coleta dados de um endpoint da API e os salva em formato JSON bruto no "Data Lake" local.
*   **Timestamp no Nome do Arquivo**: Garante que cada execução crie um novo arquivo, preservando o histórico dos dados brutos.
*   **Comentário de Cenário Real**: O script inclui um comentário explícito (`Em um cenário real, isso seria o upload para um bucket S3, Azure Blob Storage, etc.`) para conectar a simulação local com a prática em ambientes de nuvem.

**Significado para o Projeto:**

Este script ilustra como os dados brutos podem ser capturados e armazenados de forma centralizada e sem processamento inicial. Isso é crucial para a flexibilidade e escalabilidade em projetos de dados, permitindo que diferentes equipes acessem os dados em seu formato original para diversas finalidades.

## Como Executar

1.  **Executar o script:**
    ```bash
    venv/bin/python scripts/simulate_data_lake_ingestion.py
    ```
    Este comando irá:
    *   Criar a pasta `data_lake/raw/` (se ainda não existir).
    *   Baixar os dados brutos dos endpoints especificados e salvá-los como arquivos JSON.

2.  **Verificar os arquivos:**
    ```bash
    ls data_lake/raw/
    ```
    Você verá os arquivos JSON brutos que foram ingeridos, simulando o conteúdo de um Data Lake.
