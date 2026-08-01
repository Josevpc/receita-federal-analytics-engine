import json
from pathlib import Path

from receita_analytics.parser.base import SchemaDrivenParser

PROJECT_ROOT = Path(__file__).parent.parent


def load_schema(name: str) -> dict:
    with open(PROJECT_ROOT / "schemas" / f"{name}.json", encoding="utf-8") as fh:
        return json.load(fh)


def test_parses_rows_matching_schema(tmp_path):
    schema = load_schema("empresas")
    content = "11111111;EMPRESA TESTE;2062;49;10000,00;05;\r\n"
    sample_file = tmp_path / "EMPRECSV"
    sample_file.write_bytes(content.encode("latin-1"))

    parser = SchemaDrivenParser(entity_name="empresas", schema=schema, batch_size=100)
    batches = list(parser.parse(sample_file))

    assert len(batches) == 1
    assert len(batches[0]) == 1
    assert batches[0][0]["cnpj_basico"] == "11111111"
    assert batches[0][0]["razao_social"] == "EMPRESA TESTE"


def test_respects_batch_size(tmp_path):
    schema = load_schema("empresas")
    rows = ["11111111;EMPRESA A;2062;49;1000,00;05;" for _ in range(5)]
    sample_file = tmp_path / "EMPRECSV"
    sample_file.write_bytes(("\r\n".join(rows) + "\r\n").encode("latin-1"))

    parser = SchemaDrivenParser(entity_name="empresas", schema=schema, batch_size=2)
    batches = list(parser.parse(sample_file))

    assert [len(b) for b in batches] == [2, 2, 1]


def test_skips_malformed_rows(tmp_path):
    schema = load_schema("empresas")
    content = "11111111;EMPRESA OK;2062;49;1000,00;05;\r\ncoluna_faltando;2062\r\n"
    sample_file = tmp_path / "EMPRECSV"
    sample_file.write_bytes(content.encode("latin-1"))

    parser = SchemaDrivenParser(entity_name="empresas", schema=schema, batch_size=100)
    batches = list(parser.parse(sample_file))

    total_rows = sum(len(b) for b in batches)
    assert total_rows == 1
