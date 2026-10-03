import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

from curl_cffi.requests import Session as CurlSession

from backend.aquisicao.cliente import AcessoNegadoError, BloqueioAnvisaError, ErroTransitorioAnvisaError, ResultadoBusca, criar_session, baixar_pdf, buscar_bulas
from backend.aquisicao.referencia import carregar_nomes_comerciais
from backend.aquisicao.rename import carregar_nomes_rename
from backend.armazenamento.modelos import Bula, Medicamento, StatusProcessamento
from backend.armazenamento.repositorio import (
    SessionLocal,
    atualizar_status_bula,
    buscar_bula_por_id_anvisa,
    buscar_medicamento_por_nome,
    criar_bula,
    criar_medicamento,
    criar_substancias_medicamento,
    listar_substancias_por_medicamento,
)
from backend.config import settings

logger = logging.getLogger(__name__)


class ResultadoAquisicao(str, Enum):
    BAIXADO = "BAIXADO"
    SUBSTITUIDO = "SUBSTITUIDO"
    SKIP = "SKIP"
    ERRO = "ERRO"
    NAO_ENCONTRADO = "NAO_ENCONTRADO"
    REPROCESSADO = "REPROCESSADO"
    RECUPERADO = "RECUPERADO"


@dataclass
class LogAquisicao:
    nome: str
    resultado: ResultadoAquisicao
    id_bula: str | None = None
    caminho_pdf: str | None = None
    detalhe: str | None = None


@dataclass
class ResumoAquisicao:
    total: int = 0
    baixados: int = 0
    substituidos: int = 0
    reprocessados: int = 0
    recuperados: int = 0
    skips: int = 0
    nao_encontrados: int = 0
    erros: int = 0
    bloqueado: bool = False
    logs: list[LogAquisicao] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Helpers de seleção
# ---------------------------------------------------------------------------

def _selecionar_resultado(nome: str, resultados: list[ResultadoBusca]) -> ResultadoBusca | None:
    """Seleciona o resultado mais adequado da lista retornada pela ANVISA.

    Quando o nome buscado não contém "+", prefere resultados sem "+" no
    nome_produto (princípio ativo único). Usa a lista original como fallback
    caso o filtro esvazie os candidatos.
    """
    candidatos = [r for r in resultados if _escolher_id_bula(r)]
    if not candidatos:
        return None

    if "+" not in nome:
        simples = [r for r in candidatos if "+" not in r.nome_produto]
        if simples:
            return simples[0]

    return candidatos[0]


def _escolher_id_bula(resultado: ResultadoBusca) -> str | None:
    if settings.anvisa_tipo_bula == "paciente":
        return resultado.id_bula_paciente or resultado.id_bula_profissional
    return resultado.id_bula_profissional or resultado.id_bula_paciente


def _nome_arquivo(nome_medicamento: str, id_bula: str, nome_dcb: str | None = None) -> str:
    tipo = settings.anvisa_tipo_bula  # "paciente" ou "profissional"
    partes = f"{nome_dcb}__{nome_medicamento}" if nome_dcb and nome_dcb != nome_medicamento else nome_medicamento
    slug = "".join(c if c.isalnum() else "_" for c in partes)
    # IDs JWT são longos — usa só os últimos 8 chars (suficiente para unicidade)
    sufixo = id_bula[-8:] if len(id_bula) > 8 else id_bula
    return f"{tipo}__{slug}__{sufixo}.pdf"


def _salvar_pdf(conteudo: bytes, nome_arquivo: str) -> Path:
    pasta = Path(settings.bulas_dir)
    pasta.mkdir(parents=True, exist_ok=True)
    destino = pasta / nome_arquivo
    destino.write_bytes(conteudo)
    return destino


# ---------------------------------------------------------------------------
# Cache lazy das listas de referência ANVISA (A/B)
# ---------------------------------------------------------------------------

_mapa_referencia: dict[str, list[str]] | None = None


def _obter_mapa_referencia() -> dict[str, list[str]]:
    global _mapa_referencia
    if _mapa_referencia is None:
        _mapa_referencia = carregar_nomes_comerciais()
    return _mapa_referencia


def _buscar_fallback_nome_comercial(
    nome_dcb: str,
    client: CurlSession,
) -> tuple[list[ResultadoBusca], str | None]:
    """Tenta buscar via nomes comerciais das listas A/B quando o DCB não retorna resultado.

    Retorna (resultados, nome_comercial_usado) — nome_comercial_usado é None se vazio.
    """
    mapa = _obter_mapa_referencia()
    nomes_comerciais = mapa.get(nome_dcb, [])

    for nome_comercial in nomes_comerciais:
        try:
            resultados = buscar_bulas(nome_comercial, client=client)
        except BloqueioAnvisaError:
            raise
        except Exception as e:
            logger.warning("Erro ao buscar fallback '%s': %s", nome_comercial, e)
            continue

        if resultados:
            return resultados, nome_comercial

        time.sleep(settings.anvisa_delay_segundos)

    return [], None


# ---------------------------------------------------------------------------
# Retry com backoff exponencial
# ---------------------------------------------------------------------------

def _com_retry(fn, *args, **kwargs):
    """Executa fn com backoff exponencial para ErroTransitorioAnvisaError.

    Backoff: espera_inicial × 2^(tentativa-1). Após esgotar tentativas, propaga.
    """
    tentativas = settings.anvisa_retry_tentativas
    espera = settings.anvisa_retry_espera_segundos
    for tentativa in range(1, tentativas + 1):
        try:
            return fn(*args, **kwargs)
        except ErroTransitorioAnvisaError as e:
            if tentativa == tentativas:
                logger.error(
                    "Esgotadas %d tentativas apos erro transitorio: %s", tentativas, e
                )
                raise
            logger.warning(
                "Erro transitorio (tentativa %d/%d): %s — aguardando %.1fs",
                tentativa, tentativas, e, espera,
            )
            time.sleep(espera)
            espera *= 2


# ---------------------------------------------------------------------------
# Cenários de aquisição (helpers nomeados por responsabilidade)
# ---------------------------------------------------------------------------

def _skip_por_pre_checagem_local(session, nome: str, reprocessar_erro: bool) -> LogAquisicao | None:
    """Retorna SKIP se já existe PDF válido em disco, evitando qualquer request ANVISA."""
    if reprocessar_erro:
        return None
    med = buscar_medicamento_por_nome(session, nome)
    if not med:
        return None
    bulas_validas = [
        b for b in med.bulas
        if b.status_processamento_ia != StatusProcessamento.ERRO
        and b.caminho_pdf
        and Path(b.caminho_pdf).exists()
    ]
    if not bulas_validas:
        return None
    logger.info("Pre-checagem: '%s' tem PDF valido em disco — skip sem busca ANVISA", nome)
    return LogAquisicao(
        nome=nome,
        resultado=ResultadoAquisicao.SKIP,
        id_bula=bulas_validas[0].id_bula_anvisa,
        caminho_pdf=bulas_validas[0].caminho_pdf,
    )


def _recuperar_arquivo_ausente(
    session,
    bula_existente: Bula,
    nome: str,
    nome_dcb: str,
    id_bula: str,
    client: CurlSession,
) -> LogAquisicao:
    """Cenário B: mesmo JWT, arquivo sumiu do disco — re-baixa e atualiza o banco."""
    logger.info("Arquivo ausente para '%s' (bula %s) — re-baixando", nome, id_bula)
    try:
        conteudo_pdf = _com_retry(baixar_pdf, id_bula, client=client)
    except BloqueioAnvisaError:
        raise
    except Exception as e:
        logger.warning("Erro ao baixar PDF id=%s para '%s': %s", id_bula, nome, e)
        return LogAquisicao(nome=nome, resultado=ResultadoAquisicao.ERRO, id_bula=id_bula, detalhe=str(e))

    nome_arq = _nome_arquivo(nome, id_bula, nome_dcb=nome_dcb if nome_dcb != nome else None)
    try:
        destino = _salvar_pdf(conteudo_pdf, nome_arq)
    except Exception as e:
        logger.error("Erro ao salvar PDF '%s': %s", nome_arq, e)
        return LogAquisicao(nome=nome, resultado=ResultadoAquisicao.ERRO, id_bula=id_bula, detalhe=str(e))

    atualizar_status_bula(
        session, bula_existente.id, bula_existente.status_processamento_ia,
        caminho_pdf=str(destino),
        ultima_verificacao_anvisa=datetime.now(tz=timezone.utc),
    )
    session.commit()
    logger.info("Recuperado: '%s' -> %s", nome, destino.name)
    return LogAquisicao(
        nome=nome, resultado=ResultadoAquisicao.RECUPERADO,
        id_bula=id_bula, caminho_pdf=str(destino),
    )


def _reprocessar_bula_com_erro(session, bula_existente: Bula, nome: str, id_bula: str) -> LogAquisicao:
    """Cenário ERRO + flag: redefine status para PENDENTE para nova tentativa de extração."""
    logger.info("Reprocessando '%s' (bula %s, status ERRO)", nome, id_bula)
    atualizar_status_bula(session, bula_existente.id, StatusProcessamento.PENDENTE)
    session.commit()
    return LogAquisicao(
        nome=nome, resultado=ResultadoAquisicao.REPROCESSADO,
        id_bula=id_bula, caminho_pdf=bula_existente.caminho_pdf,
    )


def _skip_jwt_rotacionado(
    session,
    med: Medicamento,
    nome: str,
    id_bula: str,
) -> LogAquisicao | None:
    """Cenário C: JWT novo mas há PDF válido em outra entrada do banco — skip sem re-download."""
    bulas_validas = [b for b in med.bulas if b.caminho_pdf and Path(b.caminho_pdf).exists()]
    if not bulas_validas:
        return None
    logger.info("Skip '%s' — JWT rotacionado mas PDF valido ja existe em disco", nome)
    atualizar_status_bula(
        session, bulas_validas[0].id, bulas_validas[0].status_processamento_ia,
        ultima_verificacao_anvisa=datetime.now(tz=timezone.utc),
    )
    session.commit()
    return LogAquisicao(
        nome=nome, resultado=ResultadoAquisicao.SKIP,
        id_bula=id_bula, caminho_pdf=bulas_validas[0].caminho_pdf,
    )


# ---------------------------------------------------------------------------
# Dispatcher principal
# ---------------------------------------------------------------------------

def _adquirir(session, nome: str, client: CurlSession, reprocessar_erro: bool) -> LogAquisicao:
    nome_dcb = nome  # preserva o nome original da RENAME durante todo o fluxo

    # Cenário 0: PDF válido já em disco — skip sem nenhum request ANVISA
    log = _skip_por_pre_checagem_local(session, nome, reprocessar_erro)
    if log:
        return log

    # Busca na ANVISA (com fallback para nomes comerciais)
    try:
        resultados = _com_retry(buscar_bulas, nome, client=client)
    except BloqueioAnvisaError:
        raise
    except AcessoNegadoError as e:
        logger.warning("Acesso negado ao buscar '%s': %s", nome, e)
        return LogAquisicao(nome=nome, resultado=ResultadoAquisicao.ERRO, detalhe=str(e))
    except Exception as e:
        logger.warning("Erro ao buscar '%s': %s", nome, e)
        return LogAquisicao(nome=nome, resultado=ResultadoAquisicao.ERRO, detalhe=str(e))

    if not resultados:
        resultados, nome_usado = _buscar_fallback_nome_comercial(nome, client)
        if not resultados:
            logger.info("Nao encontrado na ANVISA (DCB e nomes comerciais): '%s'", nome)
            return LogAquisicao(nome=nome, resultado=ResultadoAquisicao.NAO_ENCONTRADO)
        logger.info("Fallback: '%s' encontrado via nome comercial '%s'", nome, nome_usado)
        nome = nome_usado  # nome_dcb permanece como o DCB original

    escolhido = _selecionar_resultado(nome, resultados)
    if escolhido is None:
        logger.warning("Nenhum ID de bula disponivel para '%s'", nome)
        return LogAquisicao(nome=nome, resultado=ResultadoAquisicao.NAO_ENCONTRADO)

    id_bula = _escolher_id_bula(escolhido)
    bula_existente = buscar_bula_por_id_anvisa(session, id_bula)

    if bula_existente is not None:
        if bula_existente.status_processamento_ia != StatusProcessamento.ERRO:
            # Cenário A: mesmo JWT, arquivo presente → SKIP
            if bula_existente.caminho_pdf and Path(bula_existente.caminho_pdf).exists():
                logger.info(
                    "Skip '%s' — bula %s ja existe (status=%s)",
                    nome, id_bula, bula_existente.status_processamento_ia,
                )
                atualizar_status_bula(
                    session, bula_existente.id, bula_existente.status_processamento_ia,
                    ultima_verificacao_anvisa=datetime.now(tz=timezone.utc),
                )
                session.commit()
                return LogAquisicao(
                    nome=nome, resultado=ResultadoAquisicao.SKIP,
                    id_bula=id_bula, caminho_pdf=bula_existente.caminho_pdf,
                )
            # Cenário B: mesmo JWT, arquivo sumiu → re-baixar
            return _recuperar_arquivo_ausente(session, bula_existente, nome, nome_dcb, id_bula, client)

        # Bula com ERRO: reprocessar se solicitado
        if not reprocessar_erro:
            return LogAquisicao(
                nome=nome, resultado=ResultadoAquisicao.SKIP,
                id_bula=id_bula, detalhe="status=ERRO, reprocessamento nao solicitado",
            )
        return _reprocessar_bula_com_erro(session, bula_existente, nome, id_bula)

    # JWT novo — verificar medicamento antes do download
    med = buscar_medicamento_por_nome(session, nome)
    if med:
        # Cenário C: JWT novo, PDF válido em outra entrada → skip
        log = _skip_jwt_rotacionado(session, med, nome, id_bula)
        if log:
            return log
        # Cenário D: JWT novo, sem PDF → limpar registros fantasma
        for b in med.bulas:
            logger.info("Deletando registro fantasma: bula %s (%s)", b.id_bula_anvisa, nome)
            session.delete(b)
        session.flush()

    # Download real (caminho feliz)
    try:
        conteudo_pdf = _com_retry(baixar_pdf, id_bula, client=client)
    except BloqueioAnvisaError:
        raise
    except Exception as e:
        logger.warning("Erro ao baixar PDF id=%s para '%s': %s", id_bula, nome, e)
        return LogAquisicao(nome=nome, resultado=ResultadoAquisicao.ERRO, id_bula=id_bula, detalhe=str(e))

    nome_arq = _nome_arquivo(nome, id_bula, nome_dcb=nome_dcb if nome_dcb != nome else None)
    try:
        destino = _salvar_pdf(conteudo_pdf, nome_arq)
    except Exception as e:
        logger.error("Erro ao salvar PDF '%s': %s", nome_arq, e)
        return LogAquisicao(nome=nome, resultado=ResultadoAquisicao.ERRO, id_bula=id_bula, detalhe=str(e))

    # Registrar no banco com status PENDENTE
    if med is None:
        med = criar_medicamento(session, nome_comercial=nome, nome_dcb=nome_dcb)
        if nome_dcb:
            criar_substancias_medicamento(session, med.id, nome_dcb)
    elif med.nome_dcb is None and nome_dcb:
        # Preenchimento retroativo: medicamento existia sem nome_dcb
        med.nome_dcb = nome_dcb
        session.flush()
        if not listar_substancias_por_medicamento(session, med.id):
            criar_substancias_medicamento(session, med.id, nome_dcb)

    criar_bula(
        session,
        medicamento_id=med.id,
        id_bula_anvisa=id_bula,
        caminho_pdf=str(destino),
        ultima_verificacao_anvisa=datetime.now(tz=timezone.utc),
    )
    session.commit()

    logger.info("Baixado: '%s' -> %s", nome, destino.name)
    return LogAquisicao(
        nome=nome, resultado=ResultadoAquisicao.BAIXADO,
        id_bula=id_bula, caminho_pdf=str(destino),
    )


# ---------------------------------------------------------------------------
# Ponto de entrada público
# ---------------------------------------------------------------------------

def adquirir_medicamento(
    nome: str,
    client: CurlSession,
    reprocessar_erro: bool = False,
) -> LogAquisicao:
    """Executa o ciclo completo de aquisição para um único medicamento."""
    with SessionLocal() as session:
        return _adquirir(session, nome, client, reprocessar_erro)


def executar_aquisicao(
    limite: int | None = None,
    reprocessar_erro: bool = False,
    nomes: list[str] | None = None,
) -> ResumoAquisicao:
    """Executa a aquisição completa da RENAME (ou lista customizada).

    Args:
        limite: se informado, processa apenas os primeiros N medicamentos.
        reprocessar_erro: se True, reprocessa bulas com status ERRO.
        nomes: se informado, usa esta lista em vez da RENAME.
    """
    resumo = ResumoAquisicao()

    lista = nomes if nomes is not None else carregar_nomes_rename()
    if limite:
        lista = lista[:limite]

    resumo.total = len(lista)

    with criar_session() as client:
        for nome in lista:
            try:
                log = adquirir_medicamento(nome, client=client, reprocessar_erro=reprocessar_erro)
            except BloqueioAnvisaError as e:
                logger.error("BLOQUEIO: %s — interrompendo aquisicao.", e)
                resumo.bloqueado = True
                resumo.logs.append(
                    LogAquisicao(nome=nome, resultado=ResultadoAquisicao.ERRO, detalhe=str(e))
                )
                break

            resumo.logs.append(log)

            match log.resultado:
                case ResultadoAquisicao.BAIXADO:
                    resumo.baixados += 1
                case ResultadoAquisicao.SUBSTITUIDO:
                    resumo.substituidos += 1
                case ResultadoAquisicao.REPROCESSADO:
                    resumo.reprocessados += 1
                case ResultadoAquisicao.RECUPERADO:
                    resumo.recuperados += 1
                case ResultadoAquisicao.SKIP:
                    resumo.skips += 1
                case ResultadoAquisicao.NAO_ENCONTRADO:
                    resumo.nao_encontrados += 1
                case ResultadoAquisicao.ERRO:
                    resumo.erros += 1

            time.sleep(settings.anvisa_delay_segundos)

    return resumo
