"""Pacote de parsers de entidades da Receita Federal."""
from __future__ import annotations

from ..config import Config, EntityConfig
from .base import EntityParser, SchemaDrivenParser

__all__ = ["EntityParser", "SchemaDrivenParser", "build_parser", "identify_entity_for_file"]


def build_parser(entity_config: EntityConfig, config: Config) -> EntityParser:
    """Constrói o parser adequado para uma entidade a partir do schema configurado."""
    return SchemaDrivenParser(
        entity_name=entity_config.name,
        schema=entity_config.schema,
        batch_size=config.batch_size,
    )


def identify_entity_for_file(filename: str, config: Config) -> str | None:
    """Identifica a qual entidade um arquivo extraído pertence, pelo padrão do nome."""
    import fnmatch

    for name, entity_cfg in config.entities.items():
        if fnmatch.fnmatch(filename.upper(), entity_cfg.pattern.upper()):
            return name
    return None
