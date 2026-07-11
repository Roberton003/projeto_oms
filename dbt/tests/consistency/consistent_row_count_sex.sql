-- Teste de consistência: dim_sex vs stg_sex
-- dim_sex adiciona 1 linha extra (UNK) para observações sem sexo

WITH stg AS (SELECT COUNT(*) + 1 AS expected FROM {{ ref('stg_sex') }}),
     mart AS (SELECT COUNT(*) AS actual FROM {{ ref('dim_sex') }})
SELECT 'dim_sex row count mismatch' AS failure_reason,
       stg.expected AS expected_rows, mart.actual AS actual_rows
FROM stg, mart WHERE stg.expected != mart.actual
