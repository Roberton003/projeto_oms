-- staging/stg_periods.sql
SELECT
    period_id,
    year
FROM {{ source('raw_db', 'dim_periods') }}
WHERE year IS NOT NULL
