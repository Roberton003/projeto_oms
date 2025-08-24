# Script para coletar dados da API da OMS
import requests
import pandas as pd
import os

# URL base da API
BASE_URL = "https://ghoapi.azureedge.net/api/"

def get_indicators():
    """Busca a lista de todos os indicadores disponíveis."""
    response = requests.get(f"{BASE_URL}Indicator")
    if response.status_code == 200:
        return response.json()['value']
    else:
        print("Erro ao buscar indicadores.")
        return None

def main():
    """Função principal para listar os indicadores."""
    indicators = get_indicators()
    if indicators:
        df = pd.DataFrame(indicators)
        print("Amostra de Indicadores Disponíveis:")
        print(df.head())
        # Salva a lista completa de indicadores em um arquivo CSV
        output_path = os.path.join('data', 'indicators.csv')
        df.to_csv(output_path, index=False)
        print(f"\nLista completa de indicadores salva em: {output_path}")

if __name__ == "__main__":
    main()