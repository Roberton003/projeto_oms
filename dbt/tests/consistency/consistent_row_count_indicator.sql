-- Teste de consistência: dim_indicator tem mesma contagem que stg_indicators
-- Falha se retornar linhas (contagens divergem)

WITH stg AS (SELECT COUNT(*) AS cnt FROM {{ ref('stg_indicators') }}),
     mart AS (SELECT COUNT(*) AS cnt FROM {{ ref('dim_indicator') }})
SELECT 'dim_indicator row count mismatch' AS failure_reason,
       stg.cnt AS staging_rows,
       mart.cnt AS mart_rows
FROM stg, mart
WHERE stg.cnt != mart.cnt
