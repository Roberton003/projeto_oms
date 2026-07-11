-- staging/stg_locations.sql
SELECT
    location_id,
    TRIM(country_code) AS country_code,
    NULLIF(TRIM(country_name), '') AS country_name,
    NULLIF(TRIM(region_code), '') AS region_code
FROM {{ source('raw_db', 'dim_locations') }}
