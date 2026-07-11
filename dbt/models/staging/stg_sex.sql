-- staging/stg_sex.sql
SELECT
    sex_id,
    TRIM(sex_code) AS sex_code,
    TRIM(sex_name) AS sex_name
FROM {{ source('raw_db', 'dim_sex') }}
