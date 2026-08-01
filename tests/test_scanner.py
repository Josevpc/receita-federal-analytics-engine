from pathlib import Path

from receita_analytics.config import Config, EntityConfig
from receita_analytics.scanner import Scanner
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


def test_scan_zip_files_finds_all_zips(tmp_path):
    config = make_config(tmp_path)
    create_empresas_zip(config.raw_dir)
    create_socios_zip(config.raw_dir)

    scanner = Scanner(config)
    results = scanner.scan_zip_files()

    assert len(results) == 2


def test_scan_identifies_entity_type_from_filename(tmp_path):
    config = make_config(tmp_path)
    create_empresas_zip(config.raw_dir)

    scanner = Scanner(config)
    results = scanner.scan_zip_files()

    assert results[0].entity_type == "empresas"


def test_scan_returns_empty_list_when_no_zips(tmp_path):
    config = make_config(tmp_path)
    config.raw_dir.mkdir(parents=True, exist_ok=True)

    scanner = Scanner(config)
    assert scanner.scan_zip_files() == []
