"""Extractor: extrai o conteúdo dos arquivos ZIP para o diretório de trabalho."""
from __future__ import annotations

import logging
import zipfile
from pathlib import Path

from .config import Config

logger = logging.getLogger("receita_analytics.extractor")


class ExtractionError(Exception):
    """Erro ao extrair ou validar um arquivo ZIP."""


class Extractor:
    """Extrai arquivos ZIP para `extracted_dir`, validando integridade."""

    def __init__(self, config: Config):
        self.config = config

    def validate_integrity(self, path: Path) -> bool:
        """Verifica se o ZIP não está corrompido antes de extrair."""
        try:
            with zipfile.ZipFile(path) as zf:
                bad_file = zf.testzip()
                return bad_file is None
        except zipfile.BadZipFile:
            return False

    def extract(self, zip_path: Path) -> list[Path]:
        """Extrai um ZIP para um subdiretório próprio dentro de `extracted_dir`.

        Retorna a lista de caminhos dos arquivos extraídos.
        """
        if not self.validate_integrity(zip_path):
            raise ExtractionError(f"Arquivo ZIP corrompido ou inválido: {zip_path}")

        destination = self.config.extracted_dir / zip_path.stem
        destination.mkdir(parents=True, exist_ok=True)

        extracted_files = []
        with zipfile.ZipFile(zip_path) as zf:
            for member in zf.namelist():
                zf.extract(member, path=destination)
                extracted_files.append(destination / member)

        logger.info("Extraído %s -> %d arquivo(s) em %s", zip_path.name, len(extracted_files), destination)
        return extracted_files
