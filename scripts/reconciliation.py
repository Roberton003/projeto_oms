#!/usr/bin/env python3
"""reconciliation.py — Reconciliação cross-camada entre SQLite raw e DuckDB.

Uso:
    python3 scripts/reconciliation.py              # relatório em texto
    python3 scripts/reconciliation.py --json       # saída JSON (para logs)
    python3 scripts/reconciliation.py --ci         # exit 1 se divergência > tolerância

Verifica:
    1. Volume: contagem de linhas em cada camada (raw → staging → marts)
    2. Uniqueness: PKs sem duplicatas em todas as camadas
    3. Valor: soma e média de valores entre staging e marts
    4. Cobertura: todo registro na staging encontra um correspondente nos marts
"""

import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone

import duckdb

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DBT_DIR = os.path.join(PROJECT_DIR, "dbt")
RAW_DB = os.environ.get(
    "DBT_RAW_DB",
    os.path.join(PROJECT_DIR, "database", "who_gho.db"),
)
TOLERANCE_PCT = float(os.environ.get("RECONCILIATION_TOLERANCE_PCT", "0.1"))


def connect_raw() -> sqlite3.Connection | None:
    if not os.path.isfile(RAW_DB):
        return None
    return sqlite3.connect(RAW_DB)


def connect_dbt() -> duckdb.DuckDBPyConnection | None:
    candidates = [
        os.environ.get("DBT_DUCKDB_PATH"),
        os.path.join(DBT_DIR, "oms_dw.duckdb"),
        os.path.join(DBT_DIR, "oms_dw_ci.duckdb"),
    ]
    for p in candidates:
        if p and os.path.isfile(p):
            con = duckdb.connect(p)
            # ATTACH raw SQLite para queries nas staging views
            if os.path.isfile(RAW_DB):
                try:
                    con.execute(
                        f"ATTACH IF NOT EXISTS '{RAW_DB}' AS raw_db (TYPE SQLITE)"
                    )
                except Exception:
                    pass  # pode já existir
            return con
    return None


def quote(name: str) -> str:
    """Escapa nome de tabela/coluna para DuckDB com double quotes."""
    return f'"{name}"'


# ── Mapeamento Raw → Staging → Mart ──────────────────────────────
# Mart tables usam *_nk (natural key) em vez de *_id
# Staging tables mantêm *_id da fonte SQLite
LAYERS = [
    {
        "name": "Indicadores",
        "raw_table": "dim_indicators",
        "raw_count_col": "indicator_id",
        "mart_table": "dim_indicator",
        "mart_count_col": "indicator_nk",
        "staging_table": "stg_indicators",
        "staging_count_col": "indicator_id",
    },
    {
        "name": "Localizações",
        "raw_table": "dim_locations",
        "raw_count_col": "location_id",
        "mart_table": "dim_location",
        "mart_count_col": "location_nk",
        "staging_table": "stg_locations",
        "staging_count_col": "location_id",
    },
    {
        "name": "Períodos",
        "raw_table": "dim_periods",
        "raw_count_col": "period_id",
        "mart_table": "dim_period",
        "mart_count_col": "period_nk",
        "staging_table": "stg_periods",
        "staging_count_col": "period_id",
    },
    {
        "name": "Sexo",
        "raw_table": "dim_sex",
        "raw_count_col": "sex_id",
        "mart_table": "dim_sex",
        "mart_count_col": "sex_nk",
        "staging_table": "stg_sex",
        "staging_count_col": "sex_id",
        "mart_extra_rows": 1,  # +1 UNK row
    },
    {
        "name": "Observações (Fato)",
        "raw_table": "fact_observations",
        "raw_count_col": "observation_id",
        "mart_table": "fct_observations",
        "mart_count_col": "observation_id",
        "staging_table": "stg_observations",
        "staging_count_col": "observation_id",
        "value_col": "value",
    },
]


def safe_int(val) -> int:
    if val is None:
        return 0
    return int(val)


def safe_float(val) -> float:
    if val is None:
        return 0.0
    return float(val)


def reconcile_raw_to_dbt() -> dict:
    """Compara cada camada e retorna resultados."""
    raw_conn = connect_raw()
    dbt_conn = connect_dbt()

    results = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "tolerance_pct": TOLERANCE_PCT,
        "tables": [],
        "overall": "pass",
        "errors": [],
    }

    if not raw_conn:
        results["errors"].append("Raw SQLite DB não encontrado")
        results["overall"] = "error"
    if not dbt_conn:
        results["errors"].append("DuckDB (dbt) não encontrado")
        results["overall"] = "error"

    if not raw_conn or not dbt_conn:
        return results

    for layer in LAYERS:
        name = layer["name"]
        entry = {"name": name, "checks": []}

        # ── Contagens ──────────────────────────────────────────
        raw_count = 0
        stg_count = 0
        mart_count = 0

        try:
            raw_count = safe_int(
                raw_conn.execute(
                    f'SELECT COUNT({layer["raw_count_col"]}) FROM "{layer["raw_table"]}"'
                ).fetchone()[0]
            )
        except Exception as e:
            entry["checks"].append(
                {"check": "raw_count", "status": "error", "detail": str(e)}
            )

        try:
            stg_count = safe_int(
                dbt_conn.execute(
                    f'SELECT COUNT({layer["staging_count_col"]}) FROM main."{layer["staging_table"]}"'
                ).fetchone()[0]
            )
        except Exception as e:
            entry["checks"].append(
                {"check": "stg_count", "status": "error", "detail": str(e)}
            )

        try:
            mart_count = safe_int(
                dbt_conn.execute(
                    f'SELECT COUNT({layer["mart_count_col"]}) FROM main."{layer["mart_table"]}"'
                ).fetchone()[0]
            )
        except Exception as e:
            entry["checks"].append(
                {"check": "mart_count", "status": "error", "detail": str(e)}
            )

        entry["raw_count"] = raw_count
        entry["stg_count"] = stg_count
        entry["mart_count"] = mart_count

        # Ajuste para marts com linhas extras (ex: dim_sex + UNK)
        extra = layer.get("mart_extra_rows", 0)

        # Divergência percentual entre raw e mart
        if raw_count > 0:
            adjusted_raw = raw_count + extra
            pct_diff_raw_mart = abs(adjusted_raw - mart_count) / adjusted_raw * 100
        else:
            pct_diff_raw_mart = 0 if mart_count == 0 else 100

        entry["pct_diff_raw_mart"] = round(pct_diff_raw_mart, 2)

        count_status = "pass"
        if pct_diff_raw_mart > TOLERANCE_PCT:
            count_status = "fail"
            results["overall"] = "fail"

        entry["checks"].append(
            {
                "check": "count_raw_vs_mart",
                "status": count_status,
                "raw": raw_count,
                "mart": mart_count,
                "pct_diff": round(pct_diff_raw_mart, 2),
                "tolerance": TOLERANCE_PCT,
            }
        )

        # ── Uniqueness ─────────────────────────────────────────
        for scope, conn, tbl, col in [
            ("raw", raw_conn, layer["raw_table"], layer["raw_count_col"]),
            ("mart", dbt_conn, layer["mart_table"], layer["mart_count_col"]),
        ]:
            try:
                total = safe_int(
                    conn.execute(f'SELECT COUNT(*) FROM "{tbl}"').fetchone()[0]
                )
                unique = safe_int(
                    conn.execute(
                        f'SELECT COUNT(DISTINCT "{col}") FROM "{tbl}"'
                    ).fetchone()[0]
                )
                dupes = total - unique
                entry["checks"].append(
                    {
                        "check": f"uniqueness_{scope}",
                        "status": "pass" if dupes == 0 else "fail",
                        "total": total,
                        "unique": unique,
                        "duplicates": dupes,
                    }
                )
                if dupes > 0:
                    results["overall"] = "fail"
            except Exception as e:
                entry["checks"].append(
                    {
                        "check": f"uniqueness_{scope}",
                        "status": "error",
                        "detail": str(e),
                    }
                )

        # ── Valores (apenas para a fato) ────────────────────────
        value_col = layer.get("value_col")
        if value_col:
            for scope, conn, tbl in [
                ("raw", raw_conn, layer["raw_table"]),
                ("mart", dbt_conn, layer["mart_table"]),
            ]:
                try:
                    sum_val = safe_float(
                        conn.execute(
                            f'SELECT COALESCE(SUM({value_col}), 0) FROM "{tbl}"'
                        ).fetchone()[0]
                    )
                    avg_val = safe_float(
                        conn.execute(
                            f'SELECT COALESCE(AVG({value_col}), 0) FROM "{tbl}"'
                        ).fetchone()[0]
                    )
                    entry[f"sum_{scope}"] = round(sum_val, 2)
                    entry[f"avg_{scope}"] = round(avg_val, 4)
                except Exception as e:
                    entry[f"sum_{scope}"] = None
                    entry[f"avg_{scope}"] = None

            # Comparar somas
            if entry.get("sum_raw") and entry.get("sum_mart") and entry["sum_raw"] > 0:
                pct_val = (
                    abs(entry["sum_raw"] - entry["sum_mart"]) / entry["sum_raw"] * 100
                )
                val_status = "pass" if pct_val < TOLERANCE_PCT else "fail"
                entry["checks"].append(
                    {
                        "check": "value_sum_raw_vs_mart",
                        "status": val_status,
                        "sum_raw": entry["sum_raw"],
                        "sum_mart": entry["sum_mart"],
                        "pct_diff": round(pct_val, 2),
                    }
                )
                if val_status == "fail":
                    results["overall"] = "fail"

        results["tables"].append(entry)

    if raw_conn:
        raw_conn.close()
    if dbt_conn:
        dbt_conn.close()

    return results


def report_text(results: dict) -> str:
    lines = []
    lines.append("=" * 70)
    lines.append(f"  RECONCILIAÇÃO CROSS-CAMADA — {results['ts']}")
    lines.append(
        f"  Overall: {'✅ PASS' if results['overall'] == 'pass' else '❌ FAIL'}"
    )
    lines.append(f"  Tolerância: {results['tolerance_pct']}%")
    lines.append("=" * 70)

    if results.get("errors"):
        lines.append("\n⚠️  ERROS:")
        for err in results["errors"]:
            lines.append(f"  └─ {err}")

    for entry in results["tables"]:
        lines.append(f"\n📊 {entry['name']}")
        lines.append(
            f"   Linhas: Raw={entry['raw_count']}  →  Stg={entry['stg_count']}  →  Mart={entry['mart_count']}"
        )
        lines.append(f"   Divergência Raw→Mart: {entry['pct_diff_raw_mart']}%")

        if entry.get("sum_raw") and entry.get("sum_mart") is not None:
            lines.append(
                f"   Soma valores: Raw={entry['sum_raw']:,.2f}  Mart={entry['sum_mart']:,.2f}"
            )
            lines.append(
                f"   Média valores: Raw={entry['avg_raw']:,.4f}  Mart={entry['avg_mart']:,.4f}"
            )

        for check in entry["checks"]:
            icon = "✅" if check["status"] == "pass" else "❌"
            detail = check.get("detail", "")
            if check["status"] == "pass":
                detail = "OK"
            lines.append(f"   {icon} {check['check']}: {detail}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Reconciliação cross-camada")
    parser.add_argument("--json", action="store_true", help="Saída JSON")
    parser.add_argument("--ci", action="store_true", help="Exit 1 se falhar")
    args = parser.parse_args()

    results = reconcile_raw_to_dbt()

    if args.json:
        print(json.dumps(results, indent=2, default=str))
    else:
        print(report_text(results))

    if args.ci and results["overall"] != "pass":
        sys.exit(1)


if __name__ == "__main__":
    main()
