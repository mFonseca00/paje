"""Engine de comparação entre extração e gabarito usando índice de Jaccard."""
import re
import unicodedata
from dataclasses import dataclass
from typing import Literal

from backend.extracao.schemas import ContraIndicacao, InteracaoMedicamentosa

LIMIAR_CI: float = 0.45
LIMIAR_IM: float = 0.40


# ---------------------------------------------------------------------------
# Normalização de texto
# ---------------------------------------------------------------------------

def normalizar_texto(texto: str) -> str:
    """Minúsculas, remove acentos, não-alfanuméricos → espaço, strip."""
    texto = texto.lower()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    texto = re.sub(r"[^a-z0-9]", " ", texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


# ---------------------------------------------------------------------------
# Índice de Jaccard sobre conjuntos de palavras
# ---------------------------------------------------------------------------

def jaccard(a: str, b: str) -> float:
    """Jaccard entre conjuntos de palavras normalizadas."""
    tokens_a = set(normalizar_texto(a).split())
    tokens_b = set(normalizar_texto(b).split())
    if not tokens_a and not tokens_b:
        return 1.0
    if not tokens_a or not tokens_b:
        return 0.0
    return len(tokens_a & tokens_b) / len(tokens_a | tokens_b)


# ---------------------------------------------------------------------------
# Score de similaridade para contra-indicações
# ---------------------------------------------------------------------------

def score_ci(extraida: ContraIndicacao, gabarito: ContraIndicacao) -> float:
    """s_CI = J(descricao_extraída, descricao_gabarito)."""
    return jaccard(extraida.descricao, gabarito.descricao)


# ---------------------------------------------------------------------------
# Score de similaridade para interações medicamentosas
# ---------------------------------------------------------------------------

def score_interacao(extraida: InteracaoMedicamentosa, gabarito: InteracaoMedicamentosa) -> float:
    """s_IN = 0,65 × J(referencia) + 0,35 × J(efeito) ou J(referencia) se efeito nulo."""
    j_ref = jaccard(extraida.referencia, gabarito.referencia)
    if extraida.efeito is None or gabarito.efeito is None:
        return j_ref
    j_efeito = jaccard(extraida.efeito, gabarito.efeito)
    return 0.65 * j_ref + 0.35 * j_efeito


# ---------------------------------------------------------------------------
# Matching por melhor score (sem exclusividade) + TP/FP/FN
# ---------------------------------------------------------------------------

@dataclass
class MatchResult:
    gabarito: ContraIndicacao | InteracaoMedicamentosa | None
    extraida: ContraIndicacao | InteracaoMedicamentosa | None
    score: float
    classificacao: Literal["TP", "FP", "FN"]


def comparar_contraindicacoes(
    extraidas: list[ContraIndicacao],
    gabarito: list[ContraIndicacao],
    limiar: float = LIMIAR_CI,
) -> tuple[list[MatchResult], list[MatchResult]]:
    """Compara listas de CI. Retorna (matches_gabarito, fp_list).

    matches_gabarito: uma entrada por item do gabarito (TP ou FN).
    fp_list: extraídas sem correspondência acima do limiar (FP).
    """
    matches_gabarito: list[MatchResult] = []

    for g in gabarito:
        if not extraidas:
            matches_gabarito.append(
                MatchResult(gabarito=g, extraida=None, score=0.0, classificacao="FN")
            )
            continue
        best_e = max(extraidas, key=lambda e: score_ci(e, g))
        best_score = score_ci(best_e, g)
        if best_score >= limiar:
            matches_gabarito.append(
                MatchResult(gabarito=g, extraida=best_e, score=best_score, classificacao="TP")
            )
        else:
            matches_gabarito.append(
                MatchResult(gabarito=g, extraida=None, score=best_score, classificacao="FN")
            )

    fp_list: list[MatchResult] = []
    for e in extraidas:
        if not gabarito:
            fp_list.append(
                MatchResult(gabarito=None, extraida=e, score=0.0, classificacao="FP")
            )
            continue
        best_g = max(gabarito, key=lambda g: score_ci(e, g))
        best_score = score_ci(e, best_g)
        if best_score < limiar:
            fp_list.append(
                MatchResult(gabarito=None, extraida=e, score=best_score, classificacao="FP")
            )

    return matches_gabarito, fp_list


def comparar_interacoes(
    extraidas: list[InteracaoMedicamentosa],
    gabarito: list[InteracaoMedicamentosa],
    limiar: float = LIMIAR_IM,
) -> tuple[list[MatchResult], list[MatchResult]]:
    """Compara listas de IM. Retorna (matches_gabarito, fp_list).

    matches_gabarito: uma entrada por item do gabarito (TP ou FN).
    fp_list: extraídas sem correspondência acima do limiar (FP).
    """
    matches_gabarito: list[MatchResult] = []

    for g in gabarito:
        if not extraidas:
            matches_gabarito.append(
                MatchResult(gabarito=g, extraida=None, score=0.0, classificacao="FN")
            )
            continue
        best_e = max(extraidas, key=lambda e: score_interacao(e, g))
        best_score = score_interacao(best_e, g)
        if best_score >= limiar:
            matches_gabarito.append(
                MatchResult(gabarito=g, extraida=best_e, score=best_score, classificacao="TP")
            )
        else:
            matches_gabarito.append(
                MatchResult(gabarito=g, extraida=None, score=best_score, classificacao="FN")
            )

    fp_list: list[MatchResult] = []
    for e in extraidas:
        if not gabarito:
            fp_list.append(
                MatchResult(gabarito=None, extraida=e, score=0.0, classificacao="FP")
            )
            continue
        best_g = max(gabarito, key=lambda g: score_interacao(e, g))
        best_score = score_interacao(e, best_g)
        if best_score < limiar:
            fp_list.append(
                MatchResult(gabarito=None, extraida=e, score=best_score, classificacao="FP")
            )

    return matches_gabarito, fp_list
