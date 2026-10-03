"""Pipeline de extração clínica em lote.

Responsabilidades:
- Localizar os arquivos markdown (__secoes.md / __bruto.md) para cada bula.
- Chamar o agente LLM e validar a saída contra o schema Pydantic.
- Gravar no banco: resposta bruta em JSONB, entidades normalizadas,
  status PROCESSADO ou ERRO, e versão do prompt.
- Processar em lote todas as bulas com status PENDENTE.
"""
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from backend.armazenamento.modelos import Bula, StatusProcessamento
from backend.armazenamento.repositorio import (
    SessionLocal,
    atualizar_status_bula,
    criar_contraindicacao,
    criar_interacao,
    listar_bulas_por_status,
)
from backend.config import settings
from backend.extracao.agente import extrair_bula
from backend.preprocessamento.conversor import converter_pdf_para_markdown
from backend.preprocessamento.extrator import extrair_secoes_relevantes

logger = logging.getLogger(__name__)


class ResultadoExtracao(str, Enum):
    PROCESSADO = "PROCESSADO"
    ERRO = "ERRO"
    SEM_MARKDOWN = "SEM_MARKDOWN"
    SEM_PDF = "SEM_PDF"


class ResultadoPreprocessamento(str, Enum):
    GERADO = "GERADO"
    SEM_PDF = "SEM_PDF"
    ERRO = "ERRO"
    JA_EXISTE = "JA_EXISTE"


@dataclass
class ResumoPreprocessamento:
    total: int = 0
    gerados: int = 0
    sem_pdf: int = 0
    erros: int = 0
    ja_existiam: int = 0


@dataclass
class LogExtracao:
    bula_id: int
    id_bula_anvisa: str
    resultado: ResultadoExtracao
    contraindicacoes: int = 0
    interacoes: int = 0
    detalhe: str | None = None


@dataclass
class ResumoExtracao:
    total: int = 0
    processados: int = 0
    erros: int = 0
    sem_arquivo: int = 0
    logs: list[LogExtracao] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Helpers para localização de arquivos markdown
# ---------------------------------------------------------------------------

_MARKDOWN_DIR = Path(settings.markdown_dir)


def _garantir_markdown(bula: Bula) -> tuple[Path, Path] | None:
    """Garante que os arquivos markdown existam, gerando a partir do PDF se necessário."""
    if not bula.caminho_pdf:
        return None

    pdf_path = Path(bula.caminho_pdf)
    stem = pdf_path.stem
    caminho_secoes = _MARKDOWN_DIR / f"{stem}__secoes.md"
    caminho_bruto = _MARKDOWN_DIR / f"{stem}__bruto.md"

    if caminho_secoes.exists() and caminho_bruto.exists():
        return caminho_secoes, caminho_bruto

    if not pdf_path.exists():
        return None

    try:
        logger.info("[bula %d] Gerando markdown a partir de %s", bula.id, pdf_path.name)
        _MARKDOWN_DIR.mkdir(parents=True, exist_ok=True)
        markdown = converter_pdf_para_markdown(pdf_path)
        resultado = extrair_secoes_relevantes(markdown)
        caminho_bruto.write_text(markdown, encoding="utf-8")
        caminho_secoes.write_text(resultado.texto, encoding="utf-8")
    except Exception as e:
        logger.error("[bula %d] Erro ao gerar markdown: %s", bula.id, e)
        return None

    return caminho_secoes, caminho_bruto


# ---------------------------------------------------------------------------
# Preprocessamento em lote
# ---------------------------------------------------------------------------

def executar_preprocessamento_lote(limite: int | None = None) -> ResumoPreprocessamento:
    """Pré-converte PDFs pendentes em markdown (__secoes.md / __bruto.md).

    Processa bulas com status PENDENTE cujo markdown ainda não existe.
    A extração mantém _garantir_markdown como fallback, então esta função
    é complementar — não substitui o fallback inline.
    """
    resumo = ResumoPreprocessamento()

    with SessionLocal() as session:
        bulas = listar_bulas_por_status(session, StatusProcessamento.PENDENTE)

    if limite:
        bulas = bulas[:limite]

    for bula in bulas:
        resumo.total += 1

        if not bula.caminho_pdf:
            resumo.sem_pdf += 1
            continue

        pdf_path = Path(bula.caminho_pdf)
        stem = pdf_path.stem
        caminho_secoes = _MARKDOWN_DIR / f"{stem}__secoes.md"
        caminho_bruto = _MARKDOWN_DIR / f"{stem}__bruto.md"

        if caminho_secoes.exists() and caminho_bruto.exists():
            resumo.ja_existiam += 1
            continue

        if not pdf_path.exists():
            logger.warning("[bula %d] PDF ausente: %s", bula.id, bula.caminho_pdf)
            resumo.sem_pdf += 1
            continue

        try:
            logger.info("[bula %d] Pré-convertendo %s", bula.id, pdf_path.name)
            _MARKDOWN_DIR.mkdir(parents=True, exist_ok=True)
            markdown = converter_pdf_para_markdown(pdf_path)
            resultado = extrair_secoes_relevantes(markdown)
            caminho_bruto.write_text(markdown, encoding="utf-8")
            caminho_secoes.write_text(resultado.texto, encoding="utf-8")
            resumo.gerados += 1
        except Exception as e:
            logger.error("[bula %d] Erro no preprocessamento: %s", bula.id, e)
            resumo.erros += 1

    return resumo


# ---------------------------------------------------------------------------
# Extração de uma única bula com gravação no banco
# ---------------------------------------------------------------------------

def processar_bula(bula: Bula) -> LogExtracao:
    """Extrai e persiste os dados clínicos de uma bula."""
    with SessionLocal() as session:
        return _processar(session, bula)


def _processar(session, bula: Bula) -> LogExtracao:
    caminhos = _garantir_markdown(bula)

    if caminhos is None:
        if not bula.caminho_pdf or not Path(bula.caminho_pdf).exists():
            logger.warning("[bula %d] PDF ausente em disco: %s", bula.id, bula.caminho_pdf)
            return LogExtracao(
                bula_id=bula.id,
                id_bula_anvisa=bula.id_bula_anvisa,
                resultado=ResultadoExtracao.SEM_PDF,
                detalhe="PDF não encontrado em disco",
            )
        logger.warning("[bula %d] Não foi possível gerar markdown.", bula.id)
        return LogExtracao(
            bula_id=bula.id,
            id_bula_anvisa=bula.id_bula_anvisa,
            resultado=ResultadoExtracao.SEM_MARKDOWN,
            detalhe="Markdown não disponível",
        )

    caminho_secoes, caminho_bruto = caminhos
    versao_prompt = settings.prompt_version

    try:
        extracao = extrair_bula(caminho_secoes, caminho_bruto)
    except Exception as e:
        logger.error("[bula %d] Erro na extração: %s", bula.id, e)
        atualizar_status_bula(
            session,
            bula.id,
            StatusProcessamento.ERRO,
            resposta_bruta={"erro": str(e)},
            versao_prompt=versao_prompt,
        )
        session.commit()
        return LogExtracao(
            bula_id=bula.id,
            id_bula_anvisa=bula.id_bula_anvisa,
            resultado=ResultadoExtracao.ERRO,
            detalhe=str(e),
        )

    resposta_bruta = extracao.model_dump()

    atualizar_status_bula(
        session,
        bula.id,
        StatusProcessamento.PROCESSADO,
        resposta_bruta=resposta_bruta,
        versao_prompt=versao_prompt,
    )

    for ci in extracao.contraindicacoes:
        criar_contraindicacao(session, bula_id=bula.id, texto=ci.descricao)

    for interacao in extracao.interacoes:
        criar_interacao(
            session,
            bula_id=bula.id,
            tipo=interacao.tipo,
            referencia=interacao.referencia,
            efeito=interacao.efeito,
        )

    session.commit()

    logger.info(
        "[bula %d] Processado: %d CI, %d interações",
        bula.id,
        len(extracao.contraindicacoes),
        len(extracao.interacoes),
    )

    return LogExtracao(
        bula_id=bula.id,
        id_bula_anvisa=bula.id_bula_anvisa,
        resultado=ResultadoExtracao.PROCESSADO,
        contraindicacoes=len(extracao.contraindicacoes),
        interacoes=len(extracao.interacoes),
    )


# ---------------------------------------------------------------------------
# Runner em lote
# ---------------------------------------------------------------------------

def executar_extracao(
    limite: int | None = None,
    reprocessar_erro: bool | None = None,
) -> ResumoExtracao:
    """Executa a extração para todas as bulas com status PENDENTE (ou ERRO se solicitado).

    Args:
        limite: se informado, processa no máximo N bulas.
        reprocessar_erro: se True, inclui bulas com status ERRO além das PENDENTES.
            Se None, usa o valor de settings.extracao_reprocessar_erro.
    """
    if reprocessar_erro is None:
        reprocessar_erro = settings.extracao_reprocessar_erro

    resumo = ResumoExtracao()

    with SessionLocal() as session:
        bulas = listar_bulas_por_status(session, StatusProcessamento.PENDENTE)
        if reprocessar_erro:
            bulas = bulas + listar_bulas_por_status(session, StatusProcessamento.ERRO)

    if limite:
        bulas = bulas[:limite]

    resumo.total = len(bulas)

    for bula in bulas:
        log = processar_bula(bula)
        resumo.logs.append(log)

        match log.resultado:
            case ResultadoExtracao.PROCESSADO:
                resumo.processados += 1
            case ResultadoExtracao.ERRO:
                resumo.erros += 1
            case ResultadoExtracao.SEM_MARKDOWN | ResultadoExtracao.SEM_PDF:
                resumo.sem_arquivo += 1

    return resumo
