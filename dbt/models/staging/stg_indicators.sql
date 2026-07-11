-- staging/stg_indicators.sql
-- Limpeza e padronização dos indicadores da OMS.
SELECT
    indicator_id,
    TRIM(indicator_code) AS indicator_code,
    COALESCE(NULLIF(TRIM(indicator_name), ''), 'N/A') AS indicator_name,
    COALESCE(NULLIF(TRIM(category), ''), 'UNCATEGORIZED') AS category
FROM {{ source('raw_db', 'dim_indicators') }}
