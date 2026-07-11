-- Teste de consistência: fct_observations vs stg_observations

WITH stg AS (SELECT COUNT(*) AS cnt FROM {{ ref('stg_observations') }}),
     mart AS (SELECT COUNT(*) AS cnt FROM {{ ref('fct_observations') }})
SELECT 'fct_observations row count mismatch' AS failure_reason,
       stg.cnt AS staging_rows, mart.cnt AS mart_rows
FROM stg, mart WHERE stg.cnt != mart.cnt
