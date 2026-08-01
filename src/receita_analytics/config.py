"""Carregamento e representação da configuração do pipeline."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class EntityConfig:
    """Configuração de uma entidade (empresas, socios, estabelecimentos...)."""

    name: str
    pattern: str
    schema_path: Path

    @property
    def schema(self) -> dict[str, Any]:
        with open(self.schema_path, encoding="utf-8") as fh:
            return json.load(fh)


@dataclass
class Config:
    """Configuração central do pipeline, carregada a partir de um YAML."""

    base_dir: Path
    raw_dir: Path
    extracted_dir: Path
    parquet_dir: Path
    temp_dir: Path
    encoding: str
    delimiter: str
    batch_size: int
    compression: str
    log_level: str
    log_path: Path
    duckdb_path: Path
    entities: dict[str, EntityConfig] = field(default_factory=dict)

    @classmethod
    def from_yaml(cls, config_path: str | Path) -> "Config":
        config_path = Path(config_path).resolve()
        base_dir = config_path.parent.parent  # config/config.yaml -> raiz do projeto

        with open(config_path, encoding="utf-8") as fh:
            raw = yaml.safe_load(fh)

        paths = raw.get("paths", {})
        processing = raw.get("processing", {})
        logging_cfg = raw.get("logging", {})
        duckdb_cfg = raw.get("duckdb", {})
        entities_cfg = raw.get("entities", {})

        entities = {
            name: EntityConfig(
                name=name,
                pattern=cfg["pattern"],
                schema_path=(base_dir / cfg["schema_ref"]).resolve(),
            )
            for name, cfg in entities_cfg.items()
        }

        return cls(
            base_dir=base_dir,
            raw_dir=(base_dir / paths.get("raw_dir", "data/raw")).resolve(),
            extracted_dir=(base_dir / paths.get("extracted_dir", "data/extracted")).resolve(),
            parquet_dir=(base_dir / paths.get("parquet_dir", "data/parquet")).resolve(),
            temp_dir=(base_dir / paths.get("temp_dir", "data/temp")).resolve(),
            encoding=processing.get("encoding", "latin-1"),
            delimiter=processing.get("delimiter", ";"),
            batch_size=int(processing.get("batch_size", 100_000)),
            compression=processing.get("compression", "zstd"),
            log_level=logging_cfg.get("level", "INFO"),
            log_path=(base_dir / logging_cfg.get("path", "logs/pipeline.log")).resolve(),
            duckdb_path=(base_dir / duckdb_cfg.get("database_path", "data/receita.duckdb")).resolve(),
            entities=entities,
        )

    def ensure_directories(self) -> None:
        for path in (self.raw_dir, self.extracted_dir, self.parquet_dir, self.temp_dir, self.log_path.parent):
            path.mkdir(parents=True, exist_ok=True)
