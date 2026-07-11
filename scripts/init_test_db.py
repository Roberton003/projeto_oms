#!/usr/bin/env python3
"""init_test_db.py — Cria banco SQLite de teste para CI.

Uso:
    python3 scripts/init_test_db.py [--db-path database/who_gho.db]

Cria as 5 tabelas do schema OMS (dim_indicators, dim_locations, dim_periods,
dim_sex, fact_observations) e popula com dados sintéticos mínimos que passam
nos testes dbt (unique, not_null, relationships, accepted_values).

Atenção: Sobrescreve o banco existente. Use apenas em CI ou setup local limpo.
"""

import argparse
import os
import sqlite3
import sys


def create_tables(cursor: sqlite3.Cursor) -> None:
    """Cria as 5 tabelas do schema OMS."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dim_indicators (
            indicator_id INTEGER PRIMARY KEY AUTOINCREMENT,
            indicator_code TEXT UNIQUE,
            indicator_name TEXT,
            category TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dim_locations (
            location_id INTEGER PRIMARY KEY AUTOINCREMENT,
            country_code TEXT UNIQUE,
            country_name TEXT,
            region_code TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dim_periods (
            period_id INTEGER PRIMARY KEY AUTOINCREMENT,
            year INTEGER UNIQUE
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dim_sex (
            sex_id INTEGER PRIMARY KEY AUTOINCREMENT,
            sex_code TEXT UNIQUE,
            sex_name TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fact_observations (
            observation_id INTEGER PRIMARY KEY AUTOINCREMENT,
            indicator_id INTEGER,
            location_id INTEGER,
            period_id INTEGER,
            sex_id INTEGER,
            value REAL,
            FOREIGN KEY (indicator_id) REFERENCES dim_indicators(indicator_id),
            FOREIGN KEY (location_id) REFERENCES dim_locations(location_id),
            FOREIGN KEY (period_id) REFERENCES dim_periods(period_id),
            FOREIGN KEY (sex_id) REFERENCES dim_sex(sex_id)
        )
    """)


def populate_dim_tables(cursor: sqlite3.Cursor) -> dict:
    """Popula dim tables e retorna mapeamento de IDs."""
    # dim_indicators (NCD category — compatível com accepted_values)
    indicators = [
        ("NCDMORT3070", "Mortality rate 30-70", "NCD"),
        ("NCDMORT2060", "Mortality rate 20-60", "NCD"),
        ("AIR_1", "Air pollution indicator", "AIR"),
    ]
    indicator_ids = {}
    for code, name, cat in indicators:
        cursor.execute(
            "INSERT INTO dim_indicators (indicator_code, indicator_name, category) VALUES (?, ?, ?)",
            (code, name, cat),
        )
        indicator_ids[code] = cursor.lastrowid

    # dim_locations
    locations = [
        ("BRA", "Brazil", "AMR"),
        ("USA", "United States", "AMR"),
        ("GBR", "United Kingdom", "EUR"),
    ]
    location_ids = {}
    for code, name, region in locations:
        cursor.execute(
            "INSERT INTO dim_locations (country_code, country_name, region_code) VALUES (?, ?, ?)",
            (code, name, region),
        )
        location_ids[code] = cursor.lastrowid

    # dim_periods
    years = [2000, 2005, 2010, 2015, 2020]
    period_ids = {}
    for year in years:
        cursor.execute("INSERT INTO dim_periods (year) VALUES (?)", (year,))
        period_ids[year] = cursor.lastrowid

    # dim_sex
    sex_codes = [("MLE", "Male"), ("FMLE", "Female"), ("BTSX", "Both sexes")]
    sex_ids = {}
    for code, name in sex_codes:
        cursor.execute(
            "INSERT INTO dim_sex (sex_code, sex_name) VALUES (?, ?)",
            (code, name),
        )
        sex_ids[code] = cursor.lastrowid

    return {
        "indicator_ids": indicator_ids,
        "location_ids": location_ids,
        "period_ids": period_ids,
        "sex_ids": sex_ids,
    }


def populate_fact_table(cursor: sqlite3.Cursor, ids: dict) -> None:
    """Popula a fato com observações sintéticas."""
    facts = [
        # (indicator_code, country_code, year, sex_code, value)
        ("NCDMORT3070", "BRA", 2000, "MLE", 250.5),
        ("NCDMORT3070", "BRA", 2000, "FMLE", 180.3),
        ("NCDMORT3070", "USA", 2005, "BTSX", 320.1),
        ("NCDMORT3070", "GBR", 2005, "MLE", 190.7),
        ("NCDMORT2060", "USA", 2010, "FMLE", 150.2),
        ("NCDMORT2060", "BRA", 2015, "MLE", 210.0),
        ("NCDMORT2060", "GBR", 2010, "BTSX", 175.8),
        ("AIR_1", "BRA", 2020, "MLE", 45.3),
        ("AIR_1", "USA", 2020, "FMLE", 38.9),
        ("AIR_1", "GBR", 2020, "BTSX", 42.1),
    ]
    for ind_code, loc_code, year, sex_code, value in facts:
        cursor.execute(
            """INSERT INTO fact_observations
               (indicator_id, location_id, period_id, sex_id, value)
               VALUES (?, ?, ?, ?, ?)""",
            (
                ids["indicator_ids"][ind_code],
                ids["location_ids"][loc_code],
                ids["period_ids"][year],
                ids["sex_ids"][sex_code],
                value,
            ),
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Cria banco SQLite de teste para CI do projeto OMS"
    )
    parser.add_argument(
        "--db-path",
        default=None,
        help="Caminho para o arquivo .db (default: database/who_gho.db relativo ao script)",
    )
    args = parser.parse_args()

    if args.db_path:
        db_path = args.db_path
    else:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(script_dir, "..", "database", "who_gho.db")

    # Garante que o diretório existe
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    # Remove DB existente para garantir estado limpo
    if os.path.exists(db_path):
        os.remove(db_path)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    create_tables(cursor)
    ids = populate_dim_tables(cursor)
    populate_fact_table(cursor, ids)

    conn.commit()
    conn.close()

    print(f"✓ Banco de teste criado: {db_path}")
    print(
        f"  Tabelas: dim_indicators, dim_locations, dim_periods, dim_sex, fact_observations"
    )
    print(f"  Linhas na fato: 10")


if __name__ == "__main__":
    main()
