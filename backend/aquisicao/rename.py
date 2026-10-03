from pathlib import Path

import openpyxl

from backend.config import settings
from backend.utils.texto import normalizar as _normalizar


def carregar_nomes_rename(caminho: str | None = None) -> list[str]:
    """Retorna lista de nomes normalizados das substâncias da RENAME (DCB, coluna A).

    Linhas com DCB vazia são ignoradas — representam apenas concentrações adicionais
    da substância já incluída.
    """
    path = Path(caminho or settings.rename_path)
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active

    nomes: list[str] = []
    for row in ws.iter_rows(min_row=4, values_only=True):
        dcb = row[0]
        if dcb and isinstance(dcb, str) and dcb.strip():
            nome = _normalizar(dcb)
            if nome and nome not in nomes:
                nomes.append(nome)

    wb.close()
    return nomes
