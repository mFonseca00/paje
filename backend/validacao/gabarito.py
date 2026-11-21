"""Loader do gabarito de validação a partir de planilha XLSX."""
import json
import logging
from dataclasses import dataclass
from pathlib import Path

import openpyxl

from backend.extracao.schemas import ContraIndicacao, ExtracacaoClinica, InteracaoMedicamentosa

logger = logging.getLogger(__name__)


@dataclass
class EntradaGabarito:
    arquivo: str
    contraindicacoes: list[ContraIndicacao]
    interacoes: list[InteracaoMedicamentosa]


def carregar_gabarito(caminho_xlsx: Path) -> dict[str, EntradaGabarito]:
    """Carrega gabarito do XLSX. Reporta erros de parse com arquivo e linha."""
    wb = openpyxl.load_workbook(caminho_xlsx, data_only=True)
    ws = wb.active

    headers: dict[str, int] = {}
    for cell in next(ws.iter_rows(min_row=1, max_row=1)):
        if cell.value is not None:
            headers[str(cell.value)] = cell.column

    col_arquivo = headers.get("arquivo")
    col_json = headers.get("json_esperado")

    if col_arquivo is None or col_json is None:
        raise ValueError(
            f"Planilha precisa de colunas 'arquivo' e 'json_esperado'. "
            f"Encontradas: {list(headers)}"
        )

    gabarito: dict[str, EntradaGabarito] = {}

    for row_num, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        arquivo = row[col_arquivo - 1]
        json_str = row[col_json - 1]

        if not arquivo or not json_str:
            continue

        arquivo_str = str(arquivo)
        try:
            dados = json.loads(str(json_str))
            extracao = ExtracacaoClinica.model_validate(dados)
            gabarito[arquivo_str] = EntradaGabarito(
                arquivo=arquivo_str,
                contraindicacoes=extracao.contraindicacoes,
                interacoes=extracao.interacoes,
            )
        except json.JSONDecodeError as e:
            logger.error("Gabarito linha %d (%s): JSON inválido — %s", row_num, arquivo_str, e)
        except Exception as e:
            logger.error("Gabarito linha %d (%s): erro de schema — %s", row_num, arquivo_str, e)

    wb.close()
    return gabarito
