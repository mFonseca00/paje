from pathlib import Path

import openpyxl

from backend.config import settings
from backend.utils.texto import normalizar as _normalizar


def carregar_nomes_comerciais(
    caminho_a: str | None = None,
    caminho_b: str | None = None,
) -> dict[str, list[str]]:
    """Retorna mapeamento {farmaco_normalizado: [nome_comercial, ...]} consolidando
    as listas A e B de medicamentos de referência da ANVISA.

    Estrutura esperada nos xlsx: cabeçalho na linha 3, dados a partir da linha 4.
    Col A = FÁRMACO / ASSOCIAÇÃO, Col C = MEDICAMENTO (nome comercial).
    """
    resultado: dict[str, list[str]] = {}

    paths = [
        caminho_a or settings.referencia_lista_a_path,
        caminho_b or settings.referencia_lista_b_path,
    ]

    for caminho in paths:
        path = Path(caminho)
        if not path.exists():
            continue

        wb = openpyxl.load_workbook(path, data_only=True)
        ws = wb.active

        for row in ws.iter_rows(min_row=4, values_only=True):
            farmaco_raw = row[0]
            nome_comercial_raw = row[2]

            if not farmaco_raw or not isinstance(farmaco_raw, str):
                continue
            if not nome_comercial_raw or not isinstance(nome_comercial_raw, str):
                continue

            farmaco = _normalizar(farmaco_raw)
            nome_comercial = nome_comercial_raw.strip()

            if not farmaco or not nome_comercial:
                continue

            if farmaco not in resultado:
                resultado[farmaco] = []
            if nome_comercial not in resultado[farmaco]:
                resultado[farmaco].append(nome_comercial)

        wb.close()

    return resultado
