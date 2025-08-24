import great_expectations as gx
import os
import json
import pandas as pd
from great_expectations.core.batch import RuntimeBatchRequest

# Diretório raiz do projeto
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Diretório do Great Expectations
context_root_dir = os.path.join(project_root, 'great_expectations')
data_dir = os.path.join(project_root, 'data')
json_file_path = os.path.join(data_dir, "regions.json")

# Carrega o arquivo JSON manualmente
with open(json_file_path, 'r') as f:
    json_data = json.load(f)

# Extrai a lista de dados da chave 'value' e cria um DataFrame
dataframe = pd.DataFrame(json_data['value'])

# Carrega o contexto do Great Expectations
context = gx.get_context(context_root_dir=context_root_dir)

# Cria uma RuntimeBatchRequest para o DataFrame em memória
batch_request = RuntimeBatchRequest(
    datasource_name="pandas_filesystem",
    data_connector_name="default_runtime_data_connector_name",
    data_asset_name="regions",
    runtime_parameters={"batch_data": dataframe},  # Passa o DataFrame diretamente
    batch_identifiers={"default_identifier_name": "default_identifier"},
)

# Cria a suíte de expectativas
suite_name = "regions_suite"
try:
    context.get_expectation_suite(expectation_suite_name=suite_name)
    print(f"A suíte de expectativas '{suite_name}' já existe.")
except gx.exceptions.DataContextError:
    context.add_expectation_suite(expectation_suite_name=suite_name)
    print(f"Suíte de expectativas '{suite_name}' criada.")

# Obtém um Validator
validator = context.get_validator(
    batch_request=batch_request,
    expectation_suite_name=suite_name
)

# Adiciona as expectativas
validator.expect_column_to_exist("Code")
validator.expect_column_to_exist("Title")
validator.expect_column_values_to_not_be_null("Code")

# Salva a suíte de expectativas
validator.save_expectation_suite(discard_failed_expectations=False)

print(f"Expectativas adicionadas e suíte '{suite_name}' salva com sucesso.")
