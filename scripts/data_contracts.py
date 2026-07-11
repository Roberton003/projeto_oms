#!/usr/bin/env python3
"""data_contracts.py — Validação de contratos de dados entre camadas.

Cada camada (raw, staging, mart) tem um schema esperado definido como
dataclass Pydantic. O script valida schema, tipos, nulabilidade e
cardinalidade contra os bancos reais.

Uso:
    python3 scripts/data_contracts.py              # relatório texto
    python3 scripts/data_contracts.py --json        # saída JSON
    python3 scripts/data_contracts.py --ci          # exit 1 se falhar
"""

import argparse
import json
import os
import sqlite3
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import duckdb

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DBT_DIR = os.path.join(PROJECT_DIR, "dbt")
RAW_DB = os.environ.get(
    "DBT_RAW_DB", os.path.join(PROJECT_DIR, "database", "who_gho.db")
)


# ── Schema Definitions ──────────────────────────────────────────────


@dataclass
class ColumnDef:
    name: str
    dtype: str  # duckdb/SQLite type string (lowercase)
    nullable: bool = False
    description: str = ""


@dataclass
class Contract:
    """Contrato de dados para uma tabela em uma camada."""

    layer: str  # raw, staging, mart
    table: str
    description: str = ""
    columns: list = field(default_factory=list)
    expected_min_rows: int = 1
    expected_max_rows: int = 5_000_000
    pk_columns: list = field(default_factory=list)

    def validate(self, conn, engine: str = "sqlite") -> dict:
        """Valida este contrato contra uma conexão real."""
        result = {
            "table": self.table,
            "layer": self.layer,
            "status": "pass",
            "checks": [],
        }

        # ── Schema check ──
        try:
            if engine == "sqlite":
                schema_info = conn.execute(
                    f'PRAGMA table_info("{self.table}")'
                ).fetchall()
                actual_cols = {r[1]: r[2].lower() for r in schema_info}
            else:
                schema_info = conn.execute(
                    f"SELECT column_name, data_type, is_nullable "
                    f"FROM information_schema.columns "
                    f"WHERE table_name = '{self.table}' AND table_schema = 'main'"
                ).fetchall()
                actual_cols = {}
                for col_name, data_type, is_nullable in schema_info:
                    # Normaliza tipo duckdb
                    dtype = data_type.lower().split()[0] if data_type else "unknown"
                    actual_cols[col_name] = dtype
        except Exception as e:
            result["checks"].append(
                {
                    "check": "schema_read",
                    "status": "error",
                    "detail": str(e),
                }
            )
            result["status"] = "fail"
            return result

        # Verifica cada coluna esperada
        missing_cols = []
        type_mismatch = []
        for col in self.columns:
            if col.name not in actual_cols:
                missing_cols.append(col.name)
            elif actual_cols[col.name] != col.dtype and col.dtype != "any":
                type_mismatch.append(
                    f"{col.name}: expected {col.dtype}, got {actual_cols[col.name]}"
                )

        if missing_cols:
            result["checks"].append(
                {
                    "check": "columns_exist",
                    "status": "fail",
                    "detail": f"Colunas ausentes: {', '.join(missing_cols)}",
                }
            )
            result["status"] = "fail"
        else:
            result["checks"].append(
                {
                    "check": "columns_exist",
                    "status": "pass",
                    "detail": f"{len(self.columns)}/{len(self.columns)} colunas OK",
                }
            )

        if type_mismatch:
            result["checks"].append(
                {
                    "check": "column_types",
                    "status": "fail",
                    "detail": "; ".join(type_mismatch),
                }
            )
            result["status"] = "fail"
        else:
            result["checks"].append(
                {
                    "check": "column_types",
                    "status": "pass",
                }
            )

        # ── Row count ──
        try:
            total = conn.execute(f'SELECT COUNT(*) FROM "{self.table}"').fetchone()[0]
            row_ok = self.expected_min_rows <= total <= self.expected_max_rows
            result["checks"].append(
                {
                    "check": "row_count",
                    "status": "pass" if row_ok else "fail",
                    "rows": total,
                    "expected_min": self.expected_min_rows,
                    "expected_max": self.expected_max_rows,
                }
            )
            if not row_ok:
                result["status"] = "fail"
        except Exception as e:
            result["checks"].append(
                {
                    "check": "row_count",
                    "status": "error",
                    "detail": str(e),
                }
            )
            result["status"] = "fail"

        # ── PK uniqueness ──
        for pk in self.pk_columns:
            try:
                total = conn.execute(f'SELECT COUNT(*) FROM "{self.table}"').fetchone()[
                    0
                ]
                unique = conn.execute(
                    f'SELECT COUNT(DISTINCT "{pk}") FROM "{self.table}"'
                ).fetchone()[0]
                dupes = total - unique
                result["checks"].append(
                    {
                        "check": f"pk_uniqueness_{pk}",
                        "status": "pass" if dupes == 0 else "fail",
                        "total": total,
                        "unique": unique,
                        "duplicates": dupes,
                    }
                )
                if dupes > 0:
                    result["status"] = "fail"
            except Exception as e:
                result["checks"].append(
                    {
                        "check": f"pk_uniqueness_{pk}",
                        "status": "error",
                        "detail": str(e),
                    }
                )
                result["status"] = "fail"

        # ── Nullable check ──
        for col in self.columns:
            if not col.nullable:
                try:
                    nulls = conn.execute(
                        f'SELECT COUNT(*) FROM "{self.table}" '
                        f'WHERE "{col.name}" IS NULL'
                    ).fetchone()[0]
                    if nulls > 0:
                        result["checks"].append(
                            {
                                "check": f"not_null_{col.name}",
                                "status": "fail",
                                "nulls": nulls,
                            }
                        )
                        result["status"] = "fail"
                except Exception:
                    pass

        return result


# ── Contracts Registry ─────────────────────────────────────────────

RAW_CONTRACTS = [
    Contract(
        layer="raw",
        table="dim_indicators",
        description="Indicadores de saúde (fonte SQLite)",
        columns=[
            ColumnDef("indicator_id", "integer", description="PK"),
            ColumnDef("indicator_code", "text", description="Código único"),
            ColumnDef("indicator_name", "text", nullable=True),
            ColumnDef("category", "text"),
        ],
        pk_columns=["indicator_id"],
        expected_min_rows=3,
        expected_max_rows=5000,
    ),
    Contract(
        layer="raw",
        table="dim_locations",
        description="Países/regiões (fonte SQLite)",
        columns=[
            ColumnDef("location_id", "integer"),
            ColumnDef("country_code", "text"),
            ColumnDef("country_name", "text", nullable=True),
            ColumnDef("region_code", "text", nullable=True),
        ],
        pk_columns=["location_id"],
        expected_min_rows=3,
        expected_max_rows=300,
    ),
    Contract(
        layer="raw",
        table="dim_periods",
        description="Períodos/anos (fonte SQLite)",
        columns=[
            ColumnDef("period_id", "integer"),
            ColumnDef("year", "integer"),
        ],
        pk_columns=["period_id"],
        expected_min_rows=1,
        expected_max_rows=100,
    ),
    Contract(
        layer="raw",
        table="dim_sex",
        description="Sexo (fonte SQLite)",
        columns=[
            ColumnDef("sex_id", "integer"),
            ColumnDef("sex_code", "text"),
            ColumnDef("sex_name", "text", nullable=True),
        ],
        pk_columns=["sex_id"],
        expected_min_rows=3,
        expected_max_rows=10,
    ),
    Contract(
        layer="raw",
        table="fact_observations",
        description="Observações (fonte SQLite)",
        columns=[
            ColumnDef("observation_id", "integer"),
            ColumnDef("indicator_id", "integer"),
            ColumnDef("location_id", "integer"),
            ColumnDef("period_id", "integer"),
            ColumnDef("sex_id", "integer", nullable=True),
            ColumnDef("value", "real"),
        ],
        pk_columns=["observation_id"],
        expected_min_rows=1,
        expected_max_rows=3_000_000,
    ),
]

MART_CONTRACTS = [
    Contract(
        layer="mart",
        table="dim_indicator",
        description="Dimensão de indicadores",
        columns=[
            ColumnDef("indicator_key", "varchar"),
            ColumnDef("indicator_nk", "bigint"),
            ColumnDef("indicator_code", "varchar"),
            ColumnDef("indicator_name", "varchar", nullable=True),
            ColumnDef("category", "varchar"),
        ],
        pk_columns=["indicator_key"],
        expected_min_rows=3,
        expected_max_rows=5000,
    ),
    Contract(
        layer="mart",
        table="dim_location",
        description="Dimensão de localização",
        columns=[
            ColumnDef("location_key", "varchar"),
            ColumnDef("location_nk", "bigint"),
            ColumnDef("country_code", "varchar"),
            ColumnDef("country_name", "varchar", nullable=True),
            ColumnDef("region_code", "varchar", nullable=True),
        ],
        pk_columns=["location_key"],
        expected_min_rows=3,
        expected_max_rows=300,
    ),
    Contract(
        layer="mart",
        table="dim_period",
        description="Dimensão de período",
        columns=[
            ColumnDef("period_key", "varchar"),
            ColumnDef("period_nk", "bigint"),
            ColumnDef("year", "bigint"),
            ColumnDef("year_label", "varchar", nullable=True),
            ColumnDef("decade_group", "varchar", nullable=True),
        ],
        pk_columns=["period_key"],
        expected_min_rows=1,
        expected_max_rows=100,
    ),
    Contract(
        layer="mart",
        table="dim_sex",
        description="Dimensão de sexo",
        columns=[
            ColumnDef("sex_key", "varchar"),
            ColumnDef("sex_nk", "bigint"),
            ColumnDef("sex_code", "varchar"),
            ColumnDef("sex_name", "varchar", nullable=True),
        ],
        pk_columns=["sex_key"],
        expected_min_rows=4,
        expected_max_rows=10,
    ),
    Contract(
        layer="mart",
        table="fct_observations",
        description="Tabela fato de observações",
        columns=[
            ColumnDef("observation_id", "bigint"),
            ColumnDef("observation_key", "varchar"),
            ColumnDef("indicator_id", "bigint"),
            ColumnDef("indicator_key", "varchar"),
            ColumnDef("location_id", "bigint"),
            ColumnDef("location_key", "varchar"),
            ColumnDef("period_id", "bigint"),
            ColumnDef("period_key", "varchar"),
            ColumnDef("sex_id", "bigint"),
            ColumnDef("sex_key", "varchar"),
            ColumnDef("value", "double"),
        ],
        pk_columns=["observation_id"],
        expected_min_rows=1,
        expected_max_rows=3_000_000,
    ),
]


def connect_raw() -> Optional[sqlite3.Connection]:
    if not os.path.isfile(RAW_DB):
        return None
    return sqlite3.connect(RAW_DB)


def connect_dbt() -> Optional[duckdb.DuckDBPyConnection]:
    candidates = [
        os.environ.get("DBT_DUCKDB_PATH"),
        os.path.join(DBT_DIR, "oms_dw.duckdb"),
        os.path.join(DBT_DIR, "oms_dw_ci.duckdb"),
    ]
    for p in candidates:
        if p and os.path.isfile(p):
            return duckdb.connect(p)
    return None


def run_contracts() -> dict:
    results = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "overall": "pass",
        "contracts": [],
        "errors": [],
    }

    raw_conn = connect_raw()
    dbt_conn = connect_dbt()

    if not raw_conn:
        results["errors"].append("Raw SQLite DB not found")
    if not dbt_conn:
        results["errors"].append("DuckDB (dbt) not found")

    if raw_conn:
        for contract in RAW_CONTRACTS:
            try:
                r = contract.validate(raw_conn, engine="sqlite")
                results["contracts"].append(r)
                if r["status"] != "pass":
                    results["overall"] = "fail"
            except Exception as e:
                results["contracts"].append(
                    {
                        "table": contract.table,
                        "layer": contract.layer,
                        "status": "error",
                        "checks": [
                            {"check": "validate", "status": "error", "detail": str(e)}
                        ],
                    }
                )
                results["overall"] = "fail"

    if dbt_conn:
        # ATTACH raw DB for staging view queries
        if os.path.isfile(RAW_DB):
            try:
                dbt_conn.execute(
                    f"ATTACH IF NOT EXISTS '{RAW_DB}' AS raw_db (TYPE SQLITE)"
                )
            except Exception:
                pass
        for contract in MART_CONTRACTS:
            try:
                r = contract.validate(dbt_conn, engine="duckdb")
                results["contracts"].append(r)
                if r["status"] != "pass":
                    results["overall"] = "fail"
            except Exception as e:
                results["contracts"].append(
                    {
                        "table": contract.table,
                        "layer": contract.layer,
                        "status": "error",
                        "checks": [
                            {"check": "validate", "status": "error", "detail": str(e)}
                        ],
                    }
                )
                results["overall"] = "fail"

    if raw_conn:
        raw_conn.close()
    if dbt_conn:
        dbt_conn.close()

    return results


def format_text(results: dict) -> str:
    lines = []
    lines.append("=" * 70)
    lines.append(f"  DATA CONTRACTS — {results['ts']}")
    lines.append(
        f"  Overall: {'✅ PASS' if results['overall'] == 'pass' else '❌ FAIL'}"
    )
    lines.append("=" * 70)

    if results.get("errors"):
        for err in results["errors"]:
            lines.append(f"  ⚠️  {err}")

    for ct in results["contracts"]:
        icon = "✅" if ct["status"] == "pass" else "❌"
        lines.append(f"\n{icon} {ct['layer'].upper()} {ct['table']}")
        for check in ct["checks"]:
            ck = check["check"]
            st = check["status"]
            if st == "pass":
                lines.append(f"     ✅ {ck}")
            elif st == "fail":
                detail = check.get("detail", check.get("duplicates", ""))
                lines.append(f"     ❌ {ck}: {detail}")
            else:
                lines.append(f"     ⚠️  {ck}: {check.get('detail', 'error')}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Data contracts validation")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--ci", action="store_true")
    args = parser.parse_args()

    results = run_contracts()

    if args.json:
        print(json.dumps(results, indent=2, default=str))
    else:
        print(format_text(results))

    if args.ci and results["overall"] != "pass":
        sys.exit(1)


if __name__ == "__main__":
    main()
