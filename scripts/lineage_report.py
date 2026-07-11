#!/usr/bin/env python3
"""lineage_report.py — Extrai linhagem de dados do manifest.json do dbt.

Gera relatório de lineage em formato texto, JSON ou Mermaid,
rastreando o fluxo de dados das fontes (SQLite) até os marts (DuckDB).

Uso:
    python3 scripts/lineage_report.py                         # saída texto
    python3 scripts/lineage_report.py --format json           # saída JSON
    python3 scripts/lineage_report.py --format mermaid        # diagrama Mermaid
    python3 scripts/lineage_report.py --ci                    # exit 1 se algo errado
"""

import argparse
import json
import os
import sys
from collections import defaultdict

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MANIFEST_PATH = os.path.join(PROJECT_DIR, "dbt", "target", "manifest.json")


def load_manifest() -> dict:
    """Carrega o manifest.json gerado pelo dbt build."""
    if not os.path.isfile(MANIFEST_PATH):
        print(f"ERRO: manifest.json não encontrado em {MANIFEST_PATH}")
        print("Execute 'make build' primeiro para gerar o manifest.")
        sys.exit(1)

    with open(MANIFEST_PATH) as f:
        return json.load(f)


def extract_lineage(manifest: dict) -> dict:
    """Extrai lineage: sources → models com colunas e testes."""
    lineage = {
        "sources": {},
        "models": {},
        "tests": [],
        "edges": [],  # (origem, destino)
    }

    # Extrai fontes (SQLite)
    for node_id, node in manifest.get("nodes", {}).items():
        if node.get("resource_type") == "source":
            source_name = node["source_name"]
            table_name = node["name"]
            columns = {}
            for col_name, col_info in node.get("columns", {}).items():
                columns[col_name] = col_info.get("data_type", "unknown")
            lineage["sources"][f"{source_name}.{table_name}"] = {
                "name": table_name,
                "source": source_name,
                "columns": columns,
                "node_id": node_id,
            }

    # Extrai modelos (staging + marts)
    for node_id, node in manifest.get("nodes", {}).items():
        if node.get("resource_type") == "model":
            model_name = node["name"]
            columns = {}
            for col_name, col_info in node.get("columns", {}).items():
                columns[col_name] = col_info.get("data_type", "unknown")

            depends_on = []
            for dep in node.get("depends_on", {}).get("nodes", []):
                # Simplifica: source_name.table_name ou model_name
                parts = dep.split(".")
                if len(parts) >= 3 and parts[0] == "source":
                    depends_on.append(f"{parts[1]}.{parts[2]}")
                elif len(parts) >= 1:
                    depends_on.append(parts[-1])

            lineage["models"][model_name] = {
                "name": model_name,
                "columns": columns,
                "depends_on": depends_on,
                "config": {
                    "materialized": node.get("config", {}).get("materialized", "view"),
                },
                "node_id": node_id,
            }

            for dep in depends_on:
                lineage["edges"].append((dep, model_name))

    # Extrai testes
    for node_id, node in manifest.get("nodes", {}).items():
        if node.get("resource_type") == "test":
            test_info = {
                "name": node["name"],
                "model": node.get("file_key_name", ""),
                "severity": node.get("config", {}).get("severity", "error"),
                "node_id": node_id,
            }
            lineage["tests"].append(test_info)

    return lineage


def format_text(lineage: dict) -> str:
    """Formata lineage como texto."""
    lines = []
    lines.append("=" * 60)
    lines.append("  LINHAGEM DE DADOS — dbt Lineage Report")
    lines.append("=" * 60)

    # Fontes
    if lineage["sources"]:
        lines.append(f"\n📦 Fontes ({len(lineage['sources'])}):")
        for src_key, src in sorted(lineage["sources"].items()):
            lines.append(f"  {src_key}")
            for col, dtype in sorted(src["columns"].items()):
                lines.append(f"    └─ {col}: {dtype}")

    # Modelos por camada
    staging = {
        n: m
        for n, m in lineage["models"].items()
        if m["config"]["materialized"] == "view"
    }
    marts = {
        n: m
        for n, m in lineage["models"].items()
        if m["config"]["materialized"] != "view"
    }

    if staging:
        lines.append(f"\n🔷 Staging ({len(staging)}):")
        for name, model in sorted(staging.items()):
            deps = ", ".join(model["depends_on"])
            lines.append(f"  {name} ← {deps}")

    if marts:
        lines.append(f"\n🔶 Marts ({len(marts)}):")
        for name, model in sorted(marts.items()):
            deps = ", ".join(model["depends_on"])
            mat = model["config"]["materialized"]
            lines.append(f"  {name} [{mat}] ← {deps}")

    # Testes
    if lineage["tests"]:
        lines.append(f"\n✅ Testes ({len(lineage['tests'])}):")
        for t in sorted(lineage["tests"], key=lambda x: x["name"]):
            lines.append(f"  {t['name']}")

    # Grafo de dependências
    lines.append(f"\n📊 Grafo de dependências ({len(lineage['edges'])} arestas):")
    for src, dst in sorted(lineage["edges"]):
        lines.append(f"  {src} → {dst}")

    return "\n".join(lines)


def format_mermaid(lineage: dict) -> str:
    """Formata lineage como diagrama Mermaid."""
    lines = []
    lines.append("```mermaid")
    lines.append("graph LR")

    # Nós por camada
    for src_key in sorted(lineage["sources"]):
        label = src_key.split(".")[-1]
        lines.append(f"    {label}[{label}]:::source")

    staging = {
        n: m
        for n, m in lineage["models"].items()
        if m["config"]["materialized"] == "view"
    }
    marts = {
        n: m
        for n, m in lineage["models"].items()
        if m["config"]["materialized"] != "view"
    }

    for name in sorted(staging):
        lines.append(f"    {name}[{name}]:::staging")

    for name in sorted(marts):
        mat_label = (
            "incr"
            if "incremental" in str(marts[name]["config"]["materialized"])
            else "table"
        )
        lines.append(f"    {name}[{name} {mat_label}]:::mart")

    # Arestas
    for src, dst in sorted(lineage["edges"]):
        src_id = src.split(".")[-1] if "." in src else src
        lines.append(f"    {src_id} --> {dst}")

    # Estilos
    lines.append("\n    classDef source fill:#e1f5fe,stroke:#0288d1")
    lines.append("    classDef staging fill:#fff3e0,stroke:#f57c00")
    lines.append("    classDef mart fill:#e8f5e9,stroke:#388e3c")

    lines.append("```")
    return "\n".join(lines)


def format_json(lineage: dict) -> str:
    """Formata lineage como JSON."""
    # Remove node_ids para reduzir ruído
    clean = {
        "sources": {},
        "models": {},
        "tests": [],
        "edges": lineage["edges"],
    }
    for k, v in lineage["sources"].items():
        clean["sources"][k] = {"name": v["name"], "columns": list(v["columns"].keys())}
    for k, v in lineage["models"].items():
        clean["models"][k] = {
            "name": v["name"],
            "columns": list(v["columns"].keys()),
            "depends_on": v["depends_on"],
            "materialized": v["config"]["materialized"],
        }
    for t in lineage["tests"]:
        clean["tests"].append({"name": t["name"], "model": t["model"]})

    return json.dumps(clean, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description="Relatório de linhagem de dados do dbt"
    )
    parser.add_argument(
        "--format",
        choices=["text", "json", "mermaid"],
        default="text",
        help="Formato de saída (default: text)",
    )
    parser.add_argument(
        "--ci",
        action="store_true",
        help="CI mode: exit 1 se manifest não encontrado ou sem testes",
    )
    args = parser.parse_args()

    manifest = load_manifest()
    lineage = extract_lineage(manifest)

    if args.format == "json":
        print(format_json(lineage))
    elif args.format == "mermaid":
        print(format_mermaid(lineage))
    else:
        print(format_text(lineage))

    if args.ci:
        if not lineage["tests"]:
            print("\nERRO: Nenhum teste encontrado no manifest.json")
            sys.exit(1)
        if not lineage["edges"]:
            print("\nERRO: Nenhuma aresta de dependência encontrada")
            sys.exit(1)
        print(
            f"\n✅ Lineage OK: {len(lineage['sources'])} fontes, "
            f"{len(lineage['models'])} modelos, "
            f"{len(lineage['tests'])} testes, "
            f"{len(lineage['edges'])} arestas"
        )


if __name__ == "__main__":
    main()
