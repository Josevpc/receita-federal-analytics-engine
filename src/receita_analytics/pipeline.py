"""ConversionPipeline: orquestra o fluxo completo ZIP -> extração -> parsing -> Parquet."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

from .config import Config
from .extractor import ExtractionError, Extractor
from .parser import build_parser, identify_entity_for_file
from .scanner import FileMetadata, Scanner
from .writer import ParquetWriter

logger = logging.getLogger("receita_analytics.pipeline")


@dataclass
class FileResult:
    zip_file: str
    extracted_file: str
    entity: str | None
    rows_written: int
    output_path: str | None
    success: bool
    error: str | None = None


@dataclass
class PipelineResult:
    files_processed: int = 0
    files_failed: int = 0
    total_rows: int = 0
    elapsed_seconds: float = 0.0
    details: list[FileResult] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return self.files_failed == 0


class ConversionPipeline:
    """Orquestra o pipeline completo de conversão da base da Receita Federal."""

    def __init__(self, config: Config):
        self.config = config
        self.scanner = Scanner(config)
        self.extractor = Extractor(config)
        self.writer = ParquetWriter(compression=config.compression)

    def run(self) -> PipelineResult:
        self.config.ensure_directories()
        start = time.perf_counter()
        result = PipelineResult()

        zip_files = self.scanner.scan_zip_files()
        if not zip_files:
            logger.warning("Nenhum arquivo ZIP encontrado em %s", self.config.raw_dir)

        for metadata in zip_files:
            self._process_zip(metadata, result)

        result.elapsed_seconds = time.perf_counter() - start
        logger.info(
            "Pipeline concluído: %d arquivo(s) processado(s), %d falha(s), %d linha(s), %.2fs",
            result.files_processed, result.files_failed, result.total_rows, result.elapsed_seconds,
        )
        return result

    def _process_zip(self, metadata: FileMetadata, result: PipelineResult) -> None:
        try:
            extracted_files = self.extractor.extract(metadata.path)
        except ExtractionError as exc:
            logger.error("Falha ao extrair %s: %s", metadata.path.name, exc)
            result.files_failed += 1
            result.details.append(
                FileResult(
                    zip_file=metadata.path.name,
                    extracted_file="",
                    entity=metadata.entity_type,
                    rows_written=0,
                    output_path=None,
                    success=False,
                    error=str(exc),
                )
            )
            return

        for extracted_path in extracted_files:
            self._process_extracted_file(metadata, extracted_path, result)

    def _process_extracted_file(self, metadata: FileMetadata, extracted_path: Path, result: PipelineResult) -> None:
        entity_name = metadata.entity_type or identify_entity_for_file(extracted_path.name, self.config)

        if entity_name is None:
            logger.warning("Tipo de entidade não identificado para %s — ignorando", extracted_path.name)
            return

        entity_cfg = self.config.entities[entity_name]

        try:
            parser = build_parser(entity_cfg, self.config)
            schema = parser.get_schema()

            output_path = self.config.parquet_dir / entity_name / f"{extracted_path.stem}.parquet"
            rows_written = self.writer.write_batches(parser.parse(extracted_path), schema, output_path)

            result.files_processed += 1
            result.total_rows += rows_written
            result.details.append(
                FileResult(
                    zip_file=metadata.path.name,
                    extracted_file=extracted_path.name,
                    entity=entity_name,
                    rows_written=rows_written,
                    output_path=str(output_path),
                    success=True,
                )
            )
        except Exception as exc:  # noqa: BLE001 - erro de um arquivo não deve parar o pipeline
            logger.exception("Falha ao converter %s", extracted_path.name)
            result.files_failed += 1
            result.details.append(
                FileResult(
                    zip_file=metadata.path.name,
                    extracted_file=extracted_path.name,
                    entity=entity_name,
                    rows_written=0,
                    output_path=None,
                    success=False,
                    error=str(exc),
                )
            )
