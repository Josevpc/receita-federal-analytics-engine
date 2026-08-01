"""Interface de linha de comando: `receita convert|query|update|clean`."""
from __future__ import annotations

import shutil
from pathlib import Path

import typer

from .config import Config
from .duckdb_engine import DuckDBEngine
from .pipeline import ConversionPipeline
from .utils import setup_logging

app = typer.Typer(help="Receita Federal Analytics Engine — pipeline ZIP -> Parquet -> DuckDB")

DEFAULT_CONFIG = "config/config.yaml"


def _load_config(config_path: str) -> Config:
    config = Config.from_yaml(config_path)
    config.ensure_directories()
    setup_logging(config.log_path, config.log_level)
    return config


@app.command()
def convert(config_path: str = typer.Option(DEFAULT_CONFIG, "--config", "-c", help="Caminho do config.yaml")):
    """Executa o pipeline completo: ZIP -> extração -> conversão para Parquet."""
    config = _load_config(config_path)
    pipeline = ConversionPipeline(config)
    result = pipeline.run()

    typer.echo(f"Arquivos processados: {result.files_processed}")
    typer.echo(f"Arquivos com falha:   {result.files_failed}")
    typer.echo(f"Total de linhas:      {result.total_rows}")
    typer.echo(f"Tempo decorrido:      {result.elapsed_seconds:.2f}s")

    if not result.success:
        raise typer.Exit(code=1)


SUPPORTED_OUTPUT_FORMATS = {".csv", ".parquet", ".json"}


def _save_dataframe(df, output_path: Path) -> None:
    """Salva o DataFrame completo no formato indicado pela extensão de `output_path`."""
    suffix = output_path.suffix.lower()
    if suffix not in SUPPORTED_OUTPUT_FORMATS:
        supported = ", ".join(sorted(SUPPORTED_OUTPUT_FORMATS))
        raise typer.BadParameter(f"Formato '{suffix}' não suportado. Use um destes: {supported}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    if suffix == ".csv":
        df.to_csv(output_path, index=False)
    elif suffix == ".parquet":
        df.to_parquet(output_path, index=False)
    elif suffix == ".json":
        df.to_json(output_path, orient="records", force_ascii=False, indent=2)


@app.command()
def query(
    name: str = typer.Argument(..., help="Nome da consulta (arquivo .sql em consultas/, sem extensão)"),
    config_path: str = typer.Option(DEFAULT_CONFIG, "--config", "-c"),
    limit: int = typer.Option(20, help="Número máximo de linhas exibidas no terminal"),
    output: str = typer.Option(
        None, "--output", "-o", help="Salva o resultado completo em .csv, .parquet ou .json"
    ),
):
    """Executa uma consulta SQL pré-definida em `consultas/<name>.sql`."""
    config = _load_config(config_path)
    sql_path = config.base_dir / "consultas" / f"{name}.sql"

    if not sql_path.exists():
        typer.echo(f"Consulta não encontrada: {sql_path}", err=True)
        raise typer.Exit(code=1)

    engine = DuckDBEngine(config)
    try:
        df = engine.execute_file(sql_path)
        typer.echo(df.head(limit).to_string(index=False))

        if output:
            output_path = Path(output)
            _save_dataframe(df, output_path)
            typer.echo(f"\nResultado completo ({len(df)} linha(s)) salvo em: {output_path.resolve()}")
    finally:
        engine.close()


@app.command()
def update(config_path: str = typer.Option(DEFAULT_CONFIG, "--config", "-c")):
    """Reprocessa a base completa (equivalente a `convert`, reservado para futura lógica de atualização)."""
    typer.echo("Reprocessando a base completa...")
    convert(config_path=config_path)


@app.command()
def clean(
    config_path: str = typer.Option(DEFAULT_CONFIG, "--config", "-c"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Não pedir confirmação"),
):
    """Remove os diretórios `extracted/` e `parquet/`, permitindo reprocessamento do zero."""
    config = Config.from_yaml(config_path)

    if not yes:
        typer.confirm(
            f"Isso removerá {config.extracted_dir} e {config.parquet_dir}. Continuar?",
            abort=True,
        )

    for path in (config.extracted_dir, config.parquet_dir):
        if path.exists():
            shutil.rmtree(path)
            typer.echo(f"Removido: {path}")

    typer.echo("Limpeza concluída.")


if __name__ == "__main__":
    app()