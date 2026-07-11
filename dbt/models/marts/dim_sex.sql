-- marts/dim_sex.sql
-- Dimensão de sexo, com registro Unknown para observações sem classificação sexual.
WITH sex_raw AS (
    SELECT
        sex_id,
        sex_code,
        sex_name
    FROM {{ ref('stg_sex') }}

    UNION ALL

    -- Linha padrão para observações sem sexo (sex_id NULL na origem)
    SELECT
        0 AS sex_id,
        'UNK' AS sex_code,
        'Unknown' AS sex_name
)

SELECT
    {{ dbt_utils.generate_surrogate_key(['sex_id']) }} AS sex_key,
    sex_id AS sex_nk,
    sex_code,
    sex_name
FROM sex_raw
