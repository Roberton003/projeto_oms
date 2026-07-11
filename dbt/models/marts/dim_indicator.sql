-- marts/dim_indicator.sql
-- Dimensão de indicadores de saúde da OMS.
-- Materialized como table (dimensão pequena, rebuild ok).
SELECT
    {{ dbt_utils.generate_surrogate_key(['indicator_id']) }} AS indicator_key,
    indicator_id AS indicator_nk,
    indicator_code,
    indicator_name,
    category
FROM {{ ref('stg_indicators') }}
