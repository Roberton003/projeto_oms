-- staging/stg_observations.sql
-- Observações com joins mínimos para limpeza.
SELECT
    fo.observation_id,
    fo.indicator_id,
    fo.location_id,
    fo.period_id,
    fo.sex_id,
    fo.value
FROM {{ source('raw_db', 'fact_observations') }} fo
WHERE fo.value IS NOT NULL
