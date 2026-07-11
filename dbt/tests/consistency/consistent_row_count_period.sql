-- Teste de consistência: dim_period vs stg_periods

WITH stg AS (SELECT COUNT(*) AS cnt FROM {{ ref('stg_periods') }}),
     mart AS (SELECT COUNT(*) AS cnt FROM {{ ref('dim_period') }})
SELECT 'dim_period row count mismatch' AS failure_reason,
       stg.cnt AS staging_rows, mart.cnt AS mart_rows
FROM stg, mart WHERE stg.cnt != mart.cnt
