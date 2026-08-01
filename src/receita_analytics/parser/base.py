"""Interface EntityParser (Strategy Pattern) e implementação genérica baseada em schema JSON."""
from __future__ import annotations

import csv
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Iterator

logger = logging.getLogger("receita_analytics.parser")

Row = dict[str, str]


class EntityParser(ABC):
    """Contrato que todo parser de entidade da Receita Federal deve implementar."""

    entity_name: str

    @abstractmethod
    def get_schema(self) -> dict[str, Any]:
        """Retorna o schema (nomes/tipos de coluna) da entidade."""

    @abstractmethod
    def parse(self, path: Path) -> Iterator[list[Row]]:
        """Faz o parsing do arquivo em batches de linhas (dicts), para controle de memória."""


class SchemaDrivenParser(EntityParser):
    """Parser genérico que aplica um schema (JSON) carregado dinamicamente.

    Isso evita hardcode de layout no código: novas entidades só exigem um
    novo arquivo de schema em `schemas/`, conforme RF-09 do PDR.
    """

    def __init__(self, entity_name: str, schema: dict[str, Any], batch_size: int = 100_000):
        self.entity_name = entity_name
        self._schema = schema
        self.batch_size = batch_size

    def get_schema(self) -> dict[str, Any]:
        return self._schema

    def parse(self, path: Path) -> Iterator[list[Row]]:
        columns = [col["name"] for col in self._schema["columns"]]
        delimiter = self._schema.get("delimiter", ";")
        encoding = self._schema.get("encoding", "latin-1")

        batch: list[Row] = []
        with open(path, encoding=encoding, newline="") as fh:
            reader = csv.reader(fh, delimiter=delimiter, quotechar='"')
            for line_number, raw_row in enumerate(reader, start=1):
                if len(raw_row) != len(columns):
                    logger.warning(
                        "%s: linha %d com %d colunas (esperado %d) — ignorando",
                        path.name, line_number, len(raw_row), len(columns),
                    )
                    continue

                row = dict(zip(columns, raw_row))
                batch.append(row)

                if len(batch) >= self.batch_size:
                    yield batch
                    batch = []

        if batch:
            yield batch
