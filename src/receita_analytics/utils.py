"""Funções utilitárias compartilhadas entre os módulos do pipeline."""
from __future__ import annotations

import hashlib
import logging
from pathlib import Path


def setup_logging(log_path: Path, level: str = "INFO") -> logging.Logger:
    """Configura logging para console + arquivo, retornando o logger do pacote."""
    logger = logging.getLogger("receita_analytics")
    logger.setLevel(level)
    logger.handlers.clear()

    formatter = logging.Formatter(
        fmt='{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
        '"module": "%(name)s", "message": "%(message)s"}'
    )

    log_path.parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger


def file_checksum(path: Path, algorithm: str = "sha256", chunk_size: int = 8192) -> str:
    """Calcula o checksum de um arquivo em blocos, sem carregá-lo inteiro em memória."""
    hasher = hashlib.new(algorithm)
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(chunk_size), b""):
            hasher.update(chunk)
    return hasher.hexdigest()
