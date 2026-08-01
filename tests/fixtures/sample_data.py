"""Gera arquivos ZIP sintéticos que imitam o layout público da Receita Federal, para testes."""
from __future__ import annotations

import zipfile
from pathlib import Path


def create_empresas_zip(raw_dir: Path, filename: str = "K3241.K03200Y0.D60411.EMPRECSV.zip") -> Path:
    rows = [
        "11111111;EMPRESA TESTE UM LTDA;2062;49;10000,00;05;",
        "22222222;EMPRESA TESTE DOIS SA;2062;49;500000,00;03;",
        "33333333;COMERCIO TESTE TRES EIRELI;2135;50;25000,00;01;",
    ]
    return _create_zip(raw_dir, filename, "K3241.K03200Y0.D60411.EMPRECSV", rows)


def create_socios_zip(raw_dir: Path, filename: str = "K3241.K03200Y0.D60411.SOCIOCSV.zip") -> Path:
    rows = [
        "11111111;2;FULANO DE TAL;***123456**;49;20100101;;;;;5",
        "22222222;2;CICLANO SILVA;***654321**;49;20150512;;;;;6",
    ]
    return _create_zip(raw_dir, filename, "K3241.K03200Y0.D60411.SOCIOCSV", rows)


def _create_zip(raw_dir: Path, zip_filename: str, inner_filename: str, rows: list[str]) -> Path:
    raw_dir.mkdir(parents=True, exist_ok=True)
    zip_path = raw_dir / zip_filename
    content = "\r\n".join(rows) + "\r\n"

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(inner_filename, content.encode("latin-1"))

    return zip_path
