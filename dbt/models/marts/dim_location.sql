-- marts/dim_location.sql
-- Dimensão de localização geográfica (países e regiões).
WITH locations AS (
    SELECT
        {{ dbt_utils.generate_surrogate_key(['location_id']) }} AS location_key,
        location_id AS location_nk,
        country_code,
        country_name,
        region_code
    FROM {{ ref('stg_locations') }}
)

SELECT * FROM locations
