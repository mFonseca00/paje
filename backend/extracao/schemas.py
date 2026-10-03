from typing import Literal

from pydantic import BaseModel


class ContraIndicacao(BaseModel):
    ordinal: int
    descricao: str


class InteracaoMedicamentosa(BaseModel):
    ordinal: int
    tipo: Literal["NOME_DIRETO", "CLASSE", "ALIMENTO"]
    referencia: str
    efeito: str | None = None


class ExtracacaoClinica(BaseModel):
    contraindicacoes: list[ContraIndicacao]
    interacoes: list[InteracaoMedicamentosa]
