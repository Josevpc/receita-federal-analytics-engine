"""DuckDBEngine: expõe os arquivos Parquet como views SQL consultáveis via DuckDB."""
from __future__ import annotations

import logging
from pathlib import Path

import duckdb

from .config import Config

logger = logging.getLogger("receita_analytics.duckdb_engine")


class DuckDBEngine:
    """Encapsula a conexão DuckDB e o registro de views sobre os arquivos Parquet."""

    def __init__(self, config: Config):
        self.config = config
        self._connection: duckdb.DuckDBPyConnection | None = None

    def connect(self) -> duckdb.DuckDBPyConnection:
        if self._connection is None:
            self.config.duckdb_path.parent.mkdir(parents=True, exist_ok=True)
            self._connection = duckdb.connect(str(self.config.duckdb_path))
            self.register_parquet_views()
        return self._connection

    def register_parquet_views(self) -> None:
        """Cria uma view SQL para cada entidade, apontando para seus arquivos Parquet."""
        conn = self._connection
        assert conn is not None

        for entity_name in self.config.entities:
            entity_dir = self.config.parquet_dir / entity_name
            if not entity_dir.exists() or not any(entity_dir.glob("*.parquet")):
                logger.warning("Nenhum arquivo Parquet encontrado para '%s' em %s", entity_name, entity_dir)
                continue

            glob_pattern = str(entity_dir / "*.parquet")
            conn.execute(
                f"CREATE OR REPLACE VIEW {entity_name} AS "
                f"SELECT * FROM read_parquet('{glob_pattern}')"
            )
            logger.info("View '%s' registrada -> %s", entity_name, glob_pattern)

    def execute_sql(self, sql: str):
        """Executa uma string SQL arbitrária e retorna um DataFrame (pandas)."""
        conn = self.connect()
        return conn.execute(sql).df()

    def execute_file(self, sql_path: str | Path):
        """Executa o conteúdo de um arquivo .sql (ex.: consultas/empresas.sql)."""
        sql_path = Path(sql_path)
        sql = sql_path.read_text(encoding="utf-8")
        return self.execute_sql(sql)

    def close(self) -> None:
        if self._connection is not None:
            self._connection.close()
            self._connection = None
