-- staging/stg_dimensions.sql
-- Extrai dimensões auxiliares (localização, período, sexo) da camada raw.
WITH locations AS (
    SELECT
        location_id,
        country_code,
        country_name,
        region_code
    FROM {{ source('raw_db', 'dim_locations') }}
),

periods AS (
    SELECT
        period_id,
        year
    FROM {{ source('raw_db', 'dim_periods') }}
),

sex AS (
    SELECT
        sex_id,
        sex_code,
        sex_name
    FROM {{ source('raw_db', 'dim_sex') }}
)

SELECT 'locations' AS dim_type, location_id AS id, country_code AS code
FROM locations
UNION ALL
SELECT 'periods' AS dim_type, period_id, CAST(year AS VARCHAR)
FROM periods
UNION ALL
SELECT 'sex' AS dim_type, sex_id, sex_code
FROM sex
