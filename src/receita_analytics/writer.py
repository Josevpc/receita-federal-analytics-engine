"""ParquetWriter: converte batches de linhas (dicts) em arquivos Parquet."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from .parser.base import Row

logger = logging.getLogger("receita_analytics.writer")


class ParquetWriter:
    """Escreve batches de linhas em um único arquivo Parquet, de forma incremental."""

    def __init__(self, compression: str = "zstd"):
        self.compression = compression

    def write_batches(
        self,
        batches: "Any",
        schema: dict[str, Any],
        output_path: Path,
    ) -> int:
        """Consome um iterador de batches e escreve incrementalmente em `output_path`.

        Retorna o total de linhas escritas.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        column_names = [col["name"] for col in schema["columns"]]
        arrow_schema = pa.schema([(name, pa.string()) for name in column_names])

        total_rows = 0
        writer: pq.ParquetWriter | None = None
        try:
            for batch in batches:
                table = self._rows_to_table(batch, column_names, arrow_schema)
                if writer is None:
                    writer = pq.ParquetWriter(output_path, arrow_schema, compression=self.compression)
                writer.write_table(table)
                total_rows += len(batch)
        finally:
            if writer is not None:
                writer.close()

        logger.info("Escrito %s: %d linhas", output_path, total_rows)
        return total_rows

    @staticmethod
    def _rows_to_table(batch: list[Row], column_names: list[str], arrow_schema: pa.Schema) -> pa.Table:
        columns = {name: [row.get(name) for row in batch] for name in column_names}
        return pa.table(columns, schema=arrow_schema)
