-- marts/dim_period.sql
-- Dimensão de período (ano).
-- Nota: schema raw usa dim_periods, mantido como dim_period no modelo dimensional.
SELECT
    {{ dbt_utils.generate_surrogate_key(['period_id']) }} AS period_key,
    period_id AS period_nk,
    year,
    CAST(year AS VARCHAR) AS year_label,
    CASE
        WHEN year < 2000 THEN 'before_2000'
        WHEN year >= 2000 AND year < 2010 THEN '2000s'
        WHEN year >= 2010 AND year < 2020 THEN '2010s'
        ELSE '2020s'
    END AS decade_group
FROM {{ ref('stg_periods') }}
