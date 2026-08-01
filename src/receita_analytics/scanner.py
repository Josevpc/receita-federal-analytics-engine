"""Scanner: localiza arquivos ZIP na origem e identifica a entidade correspondente."""
from __future__ import annotations

import fnmatch
import logging
from dataclasses import dataclass
from pathlib import Path

from .config import Config
from .utils import file_checksum

logger = logging.getLogger("receita_analytics.scanner")


@dataclass
class FileMetadata:
    """Metadados de um arquivo ZIP encontrado na origem."""

    path: Path
    entity_type: str | None
    size_bytes: int
    checksum: str


class Scanner:
    """Localiza arquivos ZIP em `raw_dir` e identifica a que entidade pertencem."""

    def __init__(self, config: Config):
        self.config = config

    def scan_zip_files(self) -> list[FileMetadata]:
        """Retorna a lista de arquivos ZIP encontrados, com metadados básicos."""
        zip_paths = sorted(self.config.raw_dir.glob("*.zip"))
        logger.info("Encontrados %d arquivos ZIP em %s", len(zip_paths), self.config.raw_dir)

        results = []
        for path in zip_paths:
            metadata = self.get_metadata(path)
            results.append(metadata)
        return results

    def get_metadata(self, path: Path) -> FileMetadata:
        entity_type = self._identify_entity(path.name)
        return FileMetadata(
            path=path,
            entity_type=entity_type,
            size_bytes=path.stat().st_size,
            checksum=file_checksum(path),
        )

    def _identify_entity(self, filename: str) -> str | None:
        """Identifica a entidade de um ZIP pelo padrão do nome do arquivo (case-insensitive)."""
        for name, entity_cfg in self.config.entities.items():
            if fnmatch.fnmatch(filename.upper(), entity_cfg.pattern.upper()):
                return name
        return None
