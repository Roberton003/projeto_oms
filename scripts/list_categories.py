import pandas as pd
import os

# Caminho para o arquivo de dados
file_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'categorized_indicators.csv')

# Ler o arquivo CSV
df = pd.read_csv(file_path)

# Contar o número de indicadores por categoria
category_counts = df['Category'].value_counts().reset_index()
category_counts.columns = ['Categoria', 'Nº de Indicadores']

# Ordenar por contagem de indicadores (do maior para o menor)
category_counts = category_counts.sort_values(by='Nº de Indicadores', ascending=False)

print("Categorias de Indicadores Disponíveis:")
print(category_counts.to_string(index=False))
