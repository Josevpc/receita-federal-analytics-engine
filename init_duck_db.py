#!/usr/bin/env python3
"""
init_duck_db.py — Setup do banco: varredura, extração e conversão da base
da Receita Federal, com inicialização do DuckDB ao final.

Responsabilidade única deste script: deixar o DuckDB pronto e populado.
Ele varre os arquivos ZIP em `data/raw/`, extrai, converte cada entidade
para Parquet e registra as views no DuckDB (`data/receita.duckdb`).

A etapa de consulta é responsabilidade de outro script/processo, que deve
apenas abrir `data/receita.duckdb` (já pronto) e rodar SQL sobre as views —
ver `receita_analytics.duckdb_engine.DuckDBEngine` ou `python main.py query`.

Uso:
    python init_duck_db.py
    python init_duck_db.py --config config/config.yaml
    python init_duck_db.py --skip-convert          # só (re)inicializa o DuckDB sobre Parquet já existente
    python init_duck_db.py --clean-first           # limpa extracted/ e parquet/ antes de rodar
    python init_duck_db.py --raw-dir /outro/caminho
"""
from __future__ import annotations

import argparse
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from receita_analytics.config import Config  # noqa: E402
from receita_analytics.duckdb_engine import DuckDBEngine  # noqa: E402
from receita_analytics.pipeline import ConversionPipeline  # noqa: E402
from receita_analytics.utils import setup_logging  # noqa: E402

DEFAULT_CONFIG = "config/config.yaml"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Setup do banco: varredura de ZIPs -> extração -> conversão para Parquet -> DuckDB",
    )
    parser.add_argument("--config", default=DEFAULT_CONFIG, help="Caminho do config.yaml")
    parser.add_argument("--raw-dir", default=None, help="Sobrescreve o diretório de origem dos ZIPs")
    parser.add_argument(
        "--skip-convert",
        action="store_true",
        help="Pula scan/extração/conversão; apenas (re)inicializa o DuckDB sobre Parquet já existente",
    )
    parser.add_argument(
        "--clean-first",
        action="store_true",
        help="Remove extracted/ e parquet/ antes de rodar (reprocessamento do zero)",
    )
    return parser.parse_args()


def print_step(step_number: int, total: int, description: str) -> None:
    print(f"\n[{step_number}/{total}] {description}")
    print("-" * (len(description) + 8))


def clean_previous_run(config: Config) -> None:
    for path in (config.extracted_dir, config.parquet_dir):
        if path.exists():
            shutil.rmtree(path)
            print(f"  removido: {path}")


def run_conversion(config: Config) -> bool:
    """Executa scanner -> extractor -> parser -> writer. Retorna True se não houve falhas."""
    pipeline = ConversionPipeline(config)
    result = pipeline.run()

    print(f"  arquivos ZIP processados: {result.files_processed}")
    print(f"  arquivos com falha:       {result.files_failed}")
    print(f"  total de linhas gravadas: {result.total_rows:,}".replace(",", "."))
    print(f"  tempo de conversão:       {result.elapsed_seconds:.2f}s")

    if result.files_failed:
        print("\n  Falhas encontradas:")
        for detail in result.details:
            if not detail.success:
                print(f"    - {detail.zip_file} ({detail.extracted_file or 'extração'}): {detail.error}")

    return result.success


def setup_duckdb(config: Config) -> DuckDBEngine:
    engine = DuckDBEngine(config)
    engine.connect()  # já registra as views ao conectar
    return engine


def print_summary(config: Config, engine: DuckDBEngine) -> None:
    print(f"  banco DuckDB: {config.duckdb_path}")
    print(f"  views registradas:")

    for entity_name in config.entities:
        try:
            count = engine.execute_sql(f"SELECT COUNT(*) AS total FROM {entity_name}")["total"][0]
            print(f"    - {entity_name:<20} {count:>12,} linha(s)".replace(",", "."))
        except Exception:
            print(f"    - {entity_name:<20} (sem dados Parquet disponíveis)")


def main() -> int:
    args = parse_args()
    total_steps = 4
    start = time.perf_counter()

    print("=" * 60)
    print("Receita Federal Analytics Engine — Setup do DuckDB")
    print("=" * 60)

    # 1. Configuração
    print_step(1, total_steps, "Carregando configuração")
    config = Config.from_yaml(args.config)
    if args.raw_dir:
        config.raw_dir = Path(args.raw_dir).resolve()
    config.ensure_directories()
    setup_logging(config.log_path, config.log_level)
    print(f"  raw_dir:     {config.raw_dir}")
    print(f"  parquet_dir: {config.parquet_dir}")
    print(f"  duckdb_path: {config.duckdb_path}")
    print(f"  entidades:   {', '.join(config.entities)}")

    if args.clean_first:
        print_step(2, total_steps, "Limpando execução anterior")
        clean_previous_run(config)
    else:
        print_step(2, total_steps, "Limpeza anterior pulada (use --clean-first para reprocessar do zero)")

    # 3. Conversão (scan + extração + parquet)
    if args.skip_convert:
        print_step(3, total_steps, "Conversão pulada (--skip-convert)")
        conversion_ok = True
    else:
        print_step(3, total_steps, "Varrendo, extraindo e convertendo ZIPs para Parquet")
        conversion_ok = run_conversion(config)

    # 4. DuckDB
    print_step(4, total_steps, "Inicializando DuckDB e registrando views")
    engine = setup_duckdb(config)
    try:
        print_summary(config, engine)
    finally:
        engine.close()

    elapsed = time.perf_counter() - start
    print("\n" + "=" * 60)
    if conversion_ok:
        print(f"Setup concluído com sucesso em {elapsed:.2f}s.")
        print(f"Banco pronto em: {config.duckdb_path}")
        print("Use seu script/processo de consulta para ler esse arquivo diretamente.")
    else:
        print(f"Setup concluído com falhas em {elapsed:.2f}s — verifique o log em {config.log_path}")
    print("=" * 60)

    return 0 if conversion_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
