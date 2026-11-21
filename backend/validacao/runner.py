"""Orquestração da validação: extração, comparação e output versionado."""
import json
import logging
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from backend.config import settings
from backend.extracao.agente import extrair_bula
from backend.extracao.schemas import ContraIndicacao, ExtracacaoClinica, InteracaoMedicamentosa
from backend.preprocessamento.conversor import converter_pdf_para_markdown
from backend.preprocessamento.extrator import extrair_secoes_relevantes
from backend.validacao.comparador import (
    LIMIAR_CI,
    LIMIAR_IM,
    MatchResult,
    comparar_contraindicacoes,
    comparar_interacoes,
)
from backend.validacao.gabarito import EntradaGabarito, carregar_gabarito

logger = logging.getLogger(__name__)

_PDFS_DIR = Path("docs/validacao/pdfs")
_XLSX_PATH = Path("docs/validacao/referencia_validacao.xlsx")
_RESULTADOS_DIR = Path("docs/validacao/resultados")


# ---------------------------------------------------------------------------
# Métricas por micro-média
# ---------------------------------------------------------------------------

@dataclass
class Contadores:
    tp: int = 0
    fp: int = 0
    fn: int = 0

    def precisao(self) -> float:
        if self.tp + self.fp == 0:
            return 0.0
        return self.tp / (self.tp + self.fp)

    def revocacao(self) -> float:
        if self.tp + self.fn == 0:
            return 0.0
        return self.tp / (self.tp + self.fn)

    def f2(self) -> float:
        p = self.precisao()
        r = self.revocacao()
        denom = 4 * p + r
        if denom == 0:
            return 0.0
        return 5 * (p * r) / denom


# ---------------------------------------------------------------------------
# Nome da pasta de execução
# ---------------------------------------------------------------------------

def _nome_pasta_execucao() -> str:
    agora = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    prompt_versao = settings.prompt_version
    modelo = settings.llm_model.replace("/", "-")
    return f"{agora}_{prompt_versao}_{modelo}"


# ---------------------------------------------------------------------------
# Extração standalone (sem banco)
# ---------------------------------------------------------------------------

def _extrair_pdf(pdf_path: Path) -> ExtracacaoClinica | None:
    """Extrai entidades de um PDF usando temp files; não grava no banco."""
    try:
        markdown = converter_pdf_para_markdown(pdf_path)
        resultado = extrair_secoes_relevantes(markdown)
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            caminho_secoes = tmp / f"{pdf_path.stem}__secoes.md"
            caminho_bruto = tmp / f"{pdf_path.stem}__bruto.md"
            caminho_secoes.write_text(resultado.texto, encoding="utf-8")
            caminho_bruto.write_text(markdown, encoding="utf-8")
            return extrair_bula(caminho_secoes, caminho_bruto)
    except Exception as e:
        logger.error("[%s] Erro na extração: %s", pdf_path.name, e)
        return None


# ---------------------------------------------------------------------------
# Serialização do JSON por bula
# ---------------------------------------------------------------------------

def _ci_to_dict(ci: ContraIndicacao) -> dict:
    return {"descricao": ci.descricao}


def _im_to_dict(im: InteracaoMedicamentosa) -> dict:
    return {"tipo": im.tipo, "referencia": im.referencia, "efeito": im.efeito}


def _match_ci_to_dict(match: MatchResult) -> dict:
    return {
        "classificacao": match.classificacao,
        "score": round(match.score, 4),
        "gabarito": _ci_to_dict(match.gabarito) if match.gabarito else None,
        "extraida": _ci_to_dict(match.extraida) if match.extraida else None,
    }


def _match_im_to_dict(match: MatchResult) -> dict:
    return {
        "classificacao": match.classificacao,
        "score": round(match.score, 4),
        "gabarito": _im_to_dict(match.gabarito) if match.gabarito else None,
        "extraida": _im_to_dict(match.extraida) if match.extraida else None,
    }


def _gerar_json_bula(
    arquivo_nome: str,
    matches_ci: list[MatchResult],
    fp_ci: list[MatchResult],
    matches_im: list[MatchResult],
    fp_im: list[MatchResult],
) -> dict:
    ci_tp = sum(1 for m in matches_ci if m.classificacao == "TP")
    ci_fp = len(fp_ci)
    ci_fn = sum(1 for m in matches_ci if m.classificacao == "FN")
    im_tp = sum(1 for m in matches_im if m.classificacao == "TP")
    im_fp = len(fp_im)
    im_fn = sum(1 for m in matches_im if m.classificacao == "FN")

    return {
        "arquivo": arquivo_nome,
        "contraindicacoes": {
            "verdadeiro_positivo (tp)": ci_tp,
            "falso_positivo (fp)": ci_fp,
            "falso_negativo (fn)": ci_fn,
            "matches": [_match_ci_to_dict(m) for m in matches_ci + fp_ci],
        },
        "interacoes": {
            "verdadeiro_positivo (tp)": im_tp,
            "falso_positivo (fp)": im_fp,
            "falso_negativo (fn)": im_fn,
            "matches": [_match_im_to_dict(m) for m in matches_im + fp_im],
        },
    }


# ---------------------------------------------------------------------------
# relatorio.json
# ---------------------------------------------------------------------------

def _gerar_relatorio(
    total_bulas: int,
    contadores_ci: Contadores,
    contadores_im: Contadores,
    meta_revocacao: float = 0.90,
    meta_f2: float = 0.80,
) -> dict:
    p_ci = round(contadores_ci.precisao(), 4)
    r_ci = round(contadores_ci.revocacao(), 4)
    f_ci = round(contadores_ci.f2(), 4)
    aprovado_ci = r_ci >= meta_revocacao and f_ci >= meta_f2

    p_im = round(contadores_im.precisao(), 4)
    r_im = round(contadores_im.revocacao(), 4)
    f_im = round(contadores_im.f2(), 4)
    aprovado_im = r_im >= meta_revocacao and f_im >= meta_f2

    return {
        "execucao": {
            "data": datetime.now().isoformat(timespec="seconds"),
            "prompt_versao": settings.prompt_version,
            "modelo": settings.llm_model,
        },
        "total_bulas": total_bulas,
        "contraindicacoes": {
            "precisao": p_ci,
            "revocacao": r_ci,
            "f2": f_ci,
            "aprovado": aprovado_ci,
            "verdadeiro_positivo (tp)": contadores_ci.tp,
            "falso_positivo (fp)": contadores_ci.fp,
            "falso_negativo (fn)": contadores_ci.fn,
        },
        "interacoes": {
            "precisao": p_im,
            "revocacao": r_im,
            "f2": f_im,
            "aprovado": aprovado_im,
            "verdadeiro_positivo (tp)": contadores_im.tp,
            "falso_positivo (fp)": contadores_im.fp,
            "falso_negativo (fn)": contadores_im.fn,
        },
        "aprovado_geral": aprovado_ci and aprovado_im,
    }


# ---------------------------------------------------------------------------
# Orquestrador principal
# ---------------------------------------------------------------------------

def executar_validacao(
    pdfs_dir: Path = _PDFS_DIR,
    xlsx_path: Path = _XLSX_PATH,
    resultados_dir: Path = _RESULTADOS_DIR,
) -> Path:
    """Executa a validação completa. Retorna o caminho da pasta de resultados."""
    logger.info("Carregando gabarito de %s", xlsx_path)
    gabarito = carregar_gabarito(xlsx_path)
    logger.info("Gabarito carregado: %d bulas", len(gabarito))

    # Task 4.1 — pasta versionada
    pasta_execucao = resultados_dir / _nome_pasta_execucao()
    pasta_execucao.mkdir(parents=True, exist_ok=True)
    logger.info("Resultados em: %s", pasta_execucao)

    contadores_ci = Contadores()
    contadores_im = Contadores()
    total_bulas = 0

    for pdf_path in sorted(pdfs_dir.glob("*.pdf")):
        arquivo_nome = pdf_path.name

        if arquivo_nome not in gabarito:
            logger.warning("[%s] Ausente no gabarito — ignorando", arquivo_nome)
            continue

        entrada: EntradaGabarito = gabarito[arquivo_nome]
        logger.info("[%s] Extraindo...", arquivo_nome)

        extracao = _extrair_pdf(pdf_path)
        if extracao is None:
            logger.error("[%s] Extração falhou — ignorando", arquivo_nome)
            continue

        total_bulas += 1

        matches_ci, fp_ci = comparar_contraindicacoes(
            extracao.contraindicacoes, entrada.contraindicacoes, limiar=LIMIAR_CI
        )
        matches_im, fp_im = comparar_interacoes(
            extracao.interacoes, entrada.interacoes, limiar=LIMIAR_IM
        )

        # Task 4.2 — JSON por bula
        resultado_bula = _gerar_json_bula(arquivo_nome, matches_ci, fp_ci, matches_im, fp_im)
        json_path = pasta_execucao / f"{pdf_path.stem}.json"
        json_path.write_text(
            json.dumps(resultado_bula, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        ci_tp = resultado_bula["contraindicacoes"]["verdadeiro_positivo (tp)"]
        ci_fp = resultado_bula["contraindicacoes"]["falso_positivo (fp)"]
        ci_fn = resultado_bula["contraindicacoes"]["falso_negativo (fn)"]
        im_tp = resultado_bula["interacoes"]["verdadeiro_positivo (tp)"]
        im_fp = resultado_bula["interacoes"]["falso_positivo (fp)"]
        im_fn = resultado_bula["interacoes"]["falso_negativo (fn)"]

        # Task 4.3 — acumular micro-média
        contadores_ci.tp += ci_tp
        contadores_ci.fp += ci_fp
        contadores_ci.fn += ci_fn
        contadores_im.tp += im_tp
        contadores_im.fp += im_fp
        contadores_im.fn += im_fn

        logger.info(
            "[%s] ✓  CI %dTP/%dFP/%dFN  IM %dTP/%dFP/%dFN",
            arquivo_nome,
            ci_tp, ci_fp, ci_fn,
            im_tp, im_fp, im_fn,
        )

    # Task 4.4 — relatorio.json
    relatorio = _gerar_relatorio(total_bulas, contadores_ci, contadores_im)
    relatorio_path = pasta_execucao / "relatorio.json"
    relatorio_path.write_text(
        json.dumps(relatorio, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    logger.info("relatorio.json gravado em %s", relatorio_path)

    return pasta_execucao
