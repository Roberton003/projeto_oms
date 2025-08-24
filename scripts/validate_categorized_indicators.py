import great_expectations as gx
import os
from great_expectations.core.batch import RuntimeBatchRequest

# Diretório raiz do projeto
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Diretório do Great Expectations
context_root_dir = os.path.join(project_root, 'great_expectations')
data_dir = os.path.join(project_root, 'data')

# Carrega o contexto do Great Expectations
context = gx.get_context(context_root_dir=context_root_dir)

# Cria uma RuntimeBatchRequest para o arquivo CSV
batch_request = RuntimeBatchRequest(
    datasource_name="pandas_filesystem",
    data_connector_name="default_runtime_data_connector_name",
    data_asset_name="categorized_indicators",  # nome definido pelo usuário para o asset de dados
    runtime_parameters={"path": os.path.join(data_dir, "categorized_indicators.csv")},
    batch_identifiers={"default_identifier_name": "default_identifier"},
)

# Cria a suíte de expectativas
suite_name = "categorized_indicators_suite"
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
validator.expect_column_to_exist("IndicatorCode")
validator.expect_column_to_exist("IndicatorName")
validator.expect_column_to_exist("Category")
validator.expect_column_values_to_not_be_null("IndicatorCode")
validator.expect_column_values_to_not_be_null("Category")

# Salva a suíte de expectativas
validator.save_expectation_suite(discard_failed_expectations=False)

print(f"Expectativas adicionadas e suíte '{suite_name}' salva com sucesso.")
