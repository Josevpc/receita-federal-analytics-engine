from pathlib import Path

from receita_analytics.config import Config, EntityConfig
from receita_analytics.duckdb_engine import DuckDBEngine
from receita_analytics.pipeline import ConversionPipeline
from tests.fixtures.sample_data import create_empresas_zip, create_socios_zip

PROJECT_ROOT = Path(__file__).parent.parent


def make_config(tmp_path: Path) -> Config:
    return Config(
        base_dir=tmp_path,
        raw_dir=tmp_path / "raw",
        extracted_dir=tmp_path / "extracted",
        parquet_dir=tmp_path / "parquet",
        temp_dir=tmp_path / "temp",
        encoding="latin-1",
        delimiter=";",
        batch_size=10,
        compression="zstd",
        log_level="INFO",
        log_path=tmp_path / "logs" / "pipeline.log",
        duckdb_path=tmp_path / "receita.duckdb",
        entities={
            "empresas": EntityConfig("empresas", "*EMPRECSV*", PROJECT_ROOT / "schemas" / "empresas.json"),
            "socios": EntityConfig("socios", "*SOCIOCSV*", PROJECT_ROOT / "schemas" / "socios.json"),
        },
    )


def test_pipeline_converts_zip_to_parquet(tmp_path):
    config = make_config(tmp_path)
    create_empresas_zip(config.raw_dir)
    create_socios_zip(config.raw_dir)

    pipeline = ConversionPipeline(config)
    result = pipeline.run()

    assert result.success
    assert result.files_processed == 2
    assert result.total_rows == 5  # 3 empresas + 2 socios

    empresas_parquet = list((config.parquet_dir / "empresas").glob("*.parquet"))
    socios_parquet = list((config.parquet_dir / "socios").glob("*.parquet"))
    assert len(empresas_parquet) == 1
    assert len(socios_parquet) == 1


def test_pipeline_output_is_queryable_via_duckdb(tmp_path):
    config = make_config(tmp_path)
    create_empresas_zip(config.raw_dir)

    ConversionPipeline(config).run()

    engine = DuckDBEngine(config)
    try:
        df = engine.execute_sql("SELECT razao_social, capital_social FROM empresas ORDER BY razao_social")
        assert len(df) == 3
        assert "EMPRESA TESTE DOIS SA" in df["razao_social"].values
    finally:
        engine.close()


def test_pipeline_handles_empty_raw_dir_gracefully(tmp_path):
    config = make_config(tmp_path)
    config.raw_dir.mkdir(parents=True, exist_ok=True)

    result = ConversionPipeline(config).run()

    assert result.success
    assert result.files_processed == 0
    assert result.total_rows == 0
