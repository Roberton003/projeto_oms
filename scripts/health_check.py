#!/usr/bin/env python3
"""health_check.py — Verificação de integridade do pipeline OMS.

Uso:
    python3 scripts/health_check.py              # output texto
    python3 scripts/health_check.py --json       # output JSON (para logs)
    python3 scripts/health_check.py --ci         # exit 1 se algo errado (CI gate)

Verifica:
    - Existência e tamanho do banco raw SQLite
    - Existência e tamanho do banco DuckDB (dbt)
    - Contagem de linhas em cada tabela do star schema
    - Freshness (timestamp de modificação dos arquivos)
    - Integridade referencial (FKs)
"""

import argparse
import json
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone

import duckdb

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DBT_DIR = os.path.join(PROJECT_DIR, "dbt")
RAW_DB = os.environ.get(
    "DBT_RAW_DB",
    os.path.join(PROJECT_DIR, "database", "who_gho.db"),
)


def fmt_ts(t: float) -> str:
    return datetime.fromtimestamp(t, tz=timezone.utc).isoformat()


def check_raw_db() -> dict:
    """Verifica banco SQLite raw."""
    result = {
        "status": "ok",
        "path": RAW_DB,
        "exists": False,
        "size_mb": 0,
        "tables": {},
        "modified_at": None,
    }
    if not os.path.isfile(RAW_DB):
        result["status"] = "missing"
        return result

    result["exists"] = True
    result["size_mb"] = round(os.path.getsize(RAW_DB) / (1024 * 1024), 2)
    result["modified_at"] = fmt_ts(os.path.getmtime(RAW_DB))

    try:
        conn = sqlite3.connect(RAW_DB)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
        for (tbl,) in cursor.fetchall():
            count = cursor.execute(f"SELECT COUNT(*) FROM [{tbl}]").fetchone()[0]
            result["tables"][tbl] = count
        conn.close()
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)

    return result


def check_dbt_db() -> dict:
    """Verifica banco DuckDB do dbt."""
    result = {
        "status": "ok",
        "exists": False,
        "size_mb": 0,
        "tables": {},
        "modified_at": None,
    }

    # Procura DuckDB gerado pelo dbt
    candidates = [
        os.environ.get("DBT_DUCKDB_PATH"),
        os.path.join(DBT_DIR, "oms_dw.duckdb"),
        os.path.join(DBT_DIR, "oms_dw_ci.duckdb"),
    ]
    db_path = None
    for p in candidates:
        if p and os.path.isfile(p):
            db_path = p
            break

    if not db_path:
        result["status"] = "missing"
        return result

    result["path"] = db_path
    result["exists"] = True
    result["size_mb"] = round(os.path.getsize(db_path) / (1024 * 1024), 2)
    result["modified_at"] = fmt_ts(os.path.getmtime(db_path))

    try:
        con = duckdb.connect(db_path)
        tables = con.execute(
            "SELECT table_name, table_type FROM information_schema.tables "
            "WHERE table_schema = 'main' ORDER BY table_name"
        ).fetchall()
        for tbl_name, tbl_type in tables:
            count = con.execute(f'SELECT COUNT(*) FROM main."{tbl_name}"').fetchone()[0]
            result["tables"][tbl_name] = {"type": tbl_type, "rows": count}
        con.close()
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)

    return result


def check_referential_integrity() -> dict:
    """Verifica FKs: toda FK na fato encontra uma PK na dimensão."""
    result = {"status": "ok", "violations": {}}
    db_path = None
    candidates = [
        os.environ.get("DBT_DUCKDB_PATH"),
        os.path.join(DBT_DIR, "oms_dw.duckdb"),
        os.path.join(DBT_DIR, "oms_dw_ci.duckdb"),
    ]
    for p in candidates:
        if p and os.path.isfile(p):
            db_path = p
            break

    if not db_path:
        result["status"] = "no_db"
        return result

    try:
        con = duckdb.connect(db_path)
        checks = [
            ("indicator_id", "dim_indicator", "indicator_id"),
            ("location_id", "dim_location", "location_id"),
            ("period_id", "dim_period", "period_id"),
            ("sex_id", "dim_sex", "sex_id"),
        ]
        for fk_col, dim_table, dim_col in checks:
            violations = con.execute(
                f"""
                SELECT COUNT(*) AS orphans
                FROM main.fct_observations f
                LEFT JOIN main."{dim_table}" d
                    ON f."{fk_col}" = d."{dim_col}"
                WHERE d."{dim_col}" IS NULL
            """
            ).fetchone()[0]
            if violations > 0:
                result["violations"][fk_col] = violations
                result["status"] = "violations"
        con.close()
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)

    return result


def main():
    parser = argparse.ArgumentParser(description="Health check do pipeline OMS")
    parser.add_argument("--json", action="store_true", help="Saída em JSON")
    parser.add_argument("--ci", action="store_true", help="Exit 1 se algo errado")
    args = parser.parse_args()

    raw = check_raw_db()
    dbt = check_dbt_db()
    ref_int = check_referential_integrity()

    report = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "raw_db": raw,
        "dbt_db": dbt,
        "referential_integrity": ref_int,
        "overall": "ok",
    }

    if raw["status"] != "ok":
        report["overall"] = "degraded"
    if dbt["status"] != "ok":
        report["overall"] = "degraded"
    if ref_int["status"] == "violations":
        report["overall"] = "violations"

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print("=" * 60)
        print(f"  Health Check — {report['ts']}")
        print("=" * 60)
        print(f"\nOverall Status: {report['overall'].upper()}")

        print(f"\n📦 Raw DB: {raw.get('path', RAW_DB)}")
        print(f"   Exists: {raw['exists']}  |  Size: {raw['size_mb']} MB")
        if raw["tables"]:
            for tbl, cnt in raw["tables"].items():
                print(f"   └─ {tbl}: {cnt:,} rows")
        if raw.get("modified_at"):
            print(f"   Modified: {raw['modified_at']}")

        print(f"\n🐤 DuckDB (dbt):")
        print(f"   Exists: {dbt['exists']}  |  Size: {dbt['size_mb']} MB")
        if dbt["tables"]:
            for tbl, info in dbt["tables"].items():
                print(f"   └─ {tbl} ({info['type']}): {info['rows']:,} rows")

        if ref_int["violations"]:
            print(f"\n⚠️  Referential Integrity Violations:")
            for fk, cnt in ref_int["violations"].items():
                print(f"   └─ {fk}: {cnt:,} orphans")
        else:
            print(f"\n✅ Referential Integrity: OK")

        print()

    if args.ci and report["overall"] != "ok":
        sys.exit(1)


if __name__ == "__main__":
    main()
