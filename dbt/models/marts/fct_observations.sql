-- marts/fct_observations.sql
-- Tabela fato: observações de saúde por indicador, local, período e sexo.
-- Grão: cada linha = uma observação (observation_id da fonte).
-- Incremental (merge) por observation_id (PK real da fonte).

{{ config(
    materialized='incremental',
    unique_key=['observation_id'],
    on_schema_change='append_new_columns'
) }}

WITH observations AS (
    SELECT
        observation_id,
        indicator_id,
        location_id,
        period_id,
        COALESCE(sex_id, 0) AS sex_id,
        value
    FROM {{ ref('stg_observations') }}
)

SELECT
    observation_id,
    {{ dbt_utils.generate_surrogate_key(['observation_id']) }} AS observation_key,
    indicator_id,
    {{ dbt_utils.generate_surrogate_key(['indicator_id']) }} AS indicator_key,
    location_id,
    {{ dbt_utils.generate_surrogate_key(['location_id']) }} AS location_key,
    period_id,
    {{ dbt_utils.generate_surrogate_key(['period_id']) }} AS period_key,
    sex_id,
    {{ dbt_utils.generate_surrogate_key(['sex_id']) }} AS sex_key,
    value
FROM observations
