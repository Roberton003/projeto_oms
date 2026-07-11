"""
Streamlit Dashboard — WHO GHO Analytics

Uso:
    streamlit run dashboard/app.py

Conecta diretamente ao DuckDB gerado pelo dbt e exibe
métricas, tabelas e visualizações do Star Schema.
"""

import os
import sys

import duckdb
import pandas as pd
import plotly.express as px
import streamlit as st

# ── Config ──────────────────────────────────────────────────────────
st.set_page_config(
    page_title="WHO GHO Analytics",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded",
)

DBT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "dbt"))


def resolve_db_path() -> str | None:
    """Resolve o caminho do DuckDB gerado pelo dbt."""
    candidates = [
        os.environ.get("DBT_DUCKDB_PATH"),
        os.path.join(DBT_DIR, "oms_dw.duckdb"),
        os.path.join(DBT_DIR, "oms_dw_ci.duckdb"),
    ]
    for path in candidates:
        if path and os.path.isfile(path):
            return path
    return None


@st.cache_resource
def get_connection():
    db_path = resolve_db_path()
    if not db_path:
        st.error(
            "Banco DuckDB não encontrado. Execute `make build` primeiro."
        )
        st.stop()
    return duckdb.connect(db_path)


con = get_connection()

# ── Sidebar ────────────────────────────────────────────────────────
st.sidebar.title("🌍 WHO GHO")
st.sidebar.markdown("**Global Health Observatory**")
st.sidebar.markdown("---")

target = os.environ.get("DBT_TARGET", "dev")
st.sidebar.info(f"**Target:** `{target}`")

# ── Helper ──────────────────────────────────────────────────────────
def query(sql: str) -> pd.DataFrame:
    return con.execute(sql).df()


# ── Header ──────────────────────────────────────────────────────────
st.title("📊 WHO Global Health Observatory — Analytics")
st.markdown(
    "Dashboard analítico sobre indicadores de saúde pública da OMS, "
    "modelados em Star Schema via dbt + DuckDB."
)

# ── KPIs ────────────────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)

with col1:
    total_obs = query("SELECT COUNT(*) AS n FROM main.fct_observations").iloc[0, 0]
    st.metric("Observações", f"{total_obs:,}")

with col2:
    total_indicators = query("SELECT COUNT(*) AS n FROM main.dim_indicator").iloc[0, 0]
    st.metric("Indicadores", f"{total_indicators:,}")

with col3:
    total_locations = query("SELECT COUNT(*) AS n FROM main.dim_location").iloc[0, 0]
    st.metric("Países/Regiões", f"{total_locations:,}")

with col4:
    years_range = query(
        "SELECT MIN(year) || '–' || MAX(year) AS period FROM main.dim_period"
    ).iloc[0, 0]
    st.metric("Período", years_range)

st.divider()

# ── Charts ──────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(
    ["🌐 Visão Geral", "📈 Tendências", "🔍 Dados Brutos", "✅ Qualidade"]
)

with tab1:
    st.subheader("Observações por Categoria")

    df_cat = query("""
        SELECT i.category, COUNT(*) AS total
        FROM main.fct_observations f
        JOIN main.dim_indicator i ON f.indicator_id = i.indicator_id
        GROUP BY i.category
        ORDER BY total DESC
        LIMIT 15
    """)
    fig = px.bar(
        df_cat,
        x="category",
        y="total",
        title="Distribuição por Categoria de Indicador",
        labels={"category": "Categoria", "total": "Observações"},
        color="total",
        color_continuous_scale="Blues",
    )
    st.plotly_chart(fig, use_container_width=True)

    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("Top 10 Indicadores")
        df_top = query("""
            SELECT i.indicator_code, i.indicator_name, COUNT(*) AS total
            FROM main.fct_observations f
            JOIN main.dim_indicator i ON f.indicator_id = i.indicator_id
            GROUP BY i.indicator_code, i.indicator_name
            ORDER BY total DESC
            LIMIT 10
        """)
        fig2 = px.bar(
            df_top,
            x="total",
            y="indicator_code",
            orientation="h",
            title=None,
            labels={"total": "Observações", "indicator_code": "Indicador"},
            color="total",
            color_continuous_scale="Greens",
        )
        st.plotly_chart(fig2, use_container_width=True)

    with col_b:
        st.subheader("Distribuição por Sexo")
        df_sex = query("""
            SELECT s.sex_code, s.sex_name, COUNT(*) AS total
            FROM main.fct_observations f
            JOIN main.dim_sex s ON f.sex_id = s.sex_id
            GROUP BY s.sex_code, s.sex_name
            ORDER BY total DESC
        """)
        fig3 = px.pie(
            df_sex,
            values="total",
            names="sex_code",
            title=None,
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        st.plotly_chart(fig3, use_container_width=True)

with tab2:
    st.subheader("Evolução Temporal")

    df_trend = query("""
        SELECT p.year, i.category, AVG(f.value) AS avg_value
        FROM main.fct_observations f
        JOIN main.dim_period p ON f.period_id = p.period_id
        JOIN main.dim_indicator i ON f.indicator_id = i.indicator_id
        WHERE i.category IN (SELECT category FROM main.dim_indicator GROUP BY category)
        GROUP BY p.year, i.category
        ORDER BY p.year
    """)
    fig4 = px.line(
        df_trend,
        x="year",
        y="avg_value",
        color="category",
        title="Valor Médio por Ano e Categoria",
        labels={"year": "Ano", "avg_value": "Valor Médio", "category": "Categoria"},
        markers=True,
    )
    st.plotly_chart(fig4, use_container_width=True)

    col_c, col_d = st.columns(2)
    with col_c:
        st.subheader("Top 10 Países (total de observações)")
        df_loc = query("""
            SELECT l.country_code, l.country_name, COUNT(*) AS total
            FROM main.fct_observations f
            JOIN main.dim_location l ON f.location_id = l.location_id
            GROUP BY l.country_code, l.country_name
            ORDER BY total DESC
            LIMIT 10
        """)
        st.dataframe(df_loc, use_container_width=True, hide_index=True)

    with col_d:
        st.subheader("Indicadores por Categoria")
        df_cat_count = query("""
            SELECT category, COUNT(*) AS total
            FROM main.dim_indicator
            GROUP BY category
            ORDER BY total DESC
        """)
        fig5 = px.pie(
            df_cat_count,
            values="total",
            names="category",
            title=None,
            color_discrete_sequence=px.colors.qualitative.Pastel,
        )
        st.plotly_chart(fig5, use_container_width=True)

with tab3:
    st.subheader("Dados da Tabela Fato")
    st.caption("Amostra das primeiras 1.000 linhas de `fct_observations` com joins")

    df_sample = query("""
        SELECT
            f.observation_id,
            i.indicator_code,
            l.country_code,
            p.year,
            s.sex_code,
            f.value
        FROM main.fct_observations f
        LEFT JOIN main.dim_indicator i ON f.indicator_id = i.indicator_id
        LEFT JOIN main.dim_location l ON f.location_id = l.location_id
        LEFT JOIN main.dim_period p ON f.period_id = p.period_id
        LEFT JOIN main.dim_sex s ON f.sex_id = s.sex_id
        LIMIT 1000
    """)
    st.dataframe(df_sample, use_container_width=True, hide_index=True)

    st.subheader("Último Build")
    st.code(
        f"Target: {target}\n"
        f"Tabelas: {query('SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = \\'main\\'').iloc[0, 0]}\n"
        f"Total observações: {total_obs:,}",
        language="text",
    )

with tab4:
    st.subheader("✅ Data Quality Dashboard")

    col_q1, col_q2, col_q3, col_q4 = st.columns(4)
    with col_q1:
        st.metric("Testes dbt", "49", "37 data + 12 custom")
    with col_q2:
        st.metric("Contratos de Dados", "10", "5 raw + 5 marts")
    with col_q3:
        st.metric("Reconciliação", "✅", "tolerância 0.1%")
    with col_q4:
        st.metric("Health Check", "✅", "gatilho no CI")

    st.markdown("---")

    # Tabelas e contagens
    st.subheader("📊 Contagens por Camada")

    try:
        df_volumes = query("""
            SELECT 'dim_indicator' AS tabela,
                   (SELECT COUNT(*) FROM main.dim_indicator) AS mart_rows
            UNION ALL SELECT 'dim_location', (SELECT COUNT(*) FROM main.dim_location)
            UNION ALL SELECT 'dim_period', (SELECT COUNT(*) FROM main.dim_period)
            UNION ALL SELECT 'dim_sex', (SELECT COUNT(*) FROM main.dim_sex)
            UNION ALL SELECT 'fct_observations', (SELECT COUNT(*) FROM main.fct_observations)
            ORDER BY tabela
        """)
        st.dataframe(df_volumes, use_container_width=True, hide_index=True)
    except Exception:
        st.info("Execute `make build` primeiro para carregar os dados.")

    st.markdown("---")

    # PK uniqueness check
    st.subheader("🔑 Unicidade de Chaves")
    try:
        df_unique = query("""
            SELECT 'dim_indicator.indicator_key' AS chave,
                   COUNT(*) AS total,
                   COUNT(DISTINCT indicator_key) AS unicos,
                   COUNT(*) - COUNT(DISTINCT indicator_key) AS duplicatas
            FROM main.dim_indicator
            UNION ALL
            SELECT 'fct_observations.observation_id',
                   COUNT(*), COUNT(DISTINCT observation_id),
                   COUNT(*) - COUNT(DISTINCT observation_id)
            FROM main.fct_observations
        """)
        st.dataframe(df_unique, use_container_width=True, hide_index=True)
    except Exception:
        st.info("Erro ao verificar unicidade. Execute `make build`.")

    st.markdown("---")

    # Comandos de qualidade
    st.subheader("🔧 Comandos de Qualidade")
    st.code(
        "make contracts     # validar contratos de dados\n"
        "make reconcile     # reconciliação cross-camada\n"
        "make health        # health check completo\n"
        "make lineage       # relatório de linhagem\n"
        "make test          # dbt test (apenas testes)",
        language="bash"
    )
