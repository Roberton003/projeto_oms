-- Teste de consistência: dim_location vs stg_locations

WITH stg AS (SELECT COUNT(*) AS cnt FROM {{ ref('stg_locations') }}),
     mart AS (SELECT COUNT(*) AS cnt FROM {{ ref('dim_location') }})
SELECT 'dim_location row count mismatch' AS failure_reason,
       stg.cnt AS staging_rows, mart.cnt AS mart_rows
FROM stg, mart WHERE stg.cnt != mart.cnt
