import logging
from dataclasses import dataclass

from curl_cffi.requests import Session as CurlSession

from backend.config import settings

logger = logging.getLogger(__name__)

# Headers adicionais além dos que curl_cffi injeta automaticamente ao impersonar o Chrome
_HEADERS_EXTRAS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "pt-BR,pt;q=0.9",
    "Authorization": "Guest",
    "Cache-Control": "no-cache",
    "If-Modified-Since": "Mon, 26 Jul 1997 05:00:00 GMT",
    "Pragma": "no-cache",
    "Referer": "https://consultas.anvisa.gov.br/",
    "Origin": "https://consultas.anvisa.gov.br",
}


@dataclass
class ResultadoBusca:
    id_bula_paciente: str | None
    id_bula_profissional: str | None
    nome_produto: str
    expediente: str | None = None


class BloqueioAnvisaError(Exception):
    """Levantado quando a ANVISA retorna 429 ou HTML de CAPTCHA — para tudo."""


class AcessoNegadoError(Exception):
    """Levantado quando a ANVISA retorna 403 — trata como erro da bula, continua."""


class ErroTransitorioAnvisaError(Exception):
    """Levantado quando a ANVISA retorna 5xx — erro de servidor, vale retentativa."""


def _verificar_bloqueio(response) -> None:
    if response.status_code == 429:
        raise BloqueioAnvisaError(
            f"Rate-limit detectado: HTTP 429 para {response.url}"
        )
    if response.status_code == 403:
        logger.warning(
            "HTTP 403 para %s | response body: %s",
            response.url,
            response.text[:300],
        )
        raise AcessoNegadoError(
            f"Acesso negado (403) para {response.url}"
        )
    if response.status_code >= 500:
        raise ErroTransitorioAnvisaError(
            f"Erro transitorio do servidor: HTTP {response.status_code} para {response.url}"
        )
    content_type = response.headers.get("content-type", "")
    if "text/html" in content_type and response.status_code == 200:
        raise BloqueioAnvisaError(
            f"Resposta HTML inesperada (possivel CAPTCHA) para {response.url}"
        )


def criar_session() -> CurlSession:
    """Cria uma sessão curl_cffi com impersonação de Chrome (TLS fingerprint real)."""
    return CurlSession(impersonate="chrome")


def buscar_bulas(nome: str, client: CurlSession | None = None) -> list[ResultadoBusca]:
    """Consulta o endpoint bulario e retorna os registros encontrados."""
    url = f"{settings.anvisa_base_url}/api/consulta/bulario"
    params = {
        "count": 10,
        "filter[nomeProduto]": nome,
        "page": 1,
    }

    close_client = client is None
    if client is None:
        client = criar_session()

    try:
        logger.debug("Buscando '%s' em %s", nome, url)
        response = client.get(url, params=params, headers=_HEADERS_EXTRAS, timeout=30)
        _verificar_bloqueio(response)
        response.raise_for_status()

        data = response.json()
        content = data.get("content", [])

        if not content:
            logger.info("Nao encontrado: '%s' (totalElements=0)", nome)
            return []

        resultados: list[ResultadoBusca] = []
        for item in content:
            resultados.append(
                ResultadoBusca(
                    id_bula_paciente=item.get("idBulaPacienteProtegido") or None,
                    id_bula_profissional=item.get("idBulaProfissionalProtegido") or None,
                    nome_produto=item.get("nomeProduto", nome),
                    expediente=item.get("numExpediente") or None,
                )
            )
        return resultados

    finally:
        if close_client:
            client.close()


_PDF_CONTENT_TYPES = {"application/pdf", "application/force-download", "application/octet-stream"}


def baixar_pdf(id_bula: str, client: CurlSession | None = None) -> bytes:
    """Baixa o PDF da bula pelo ID. Retorna bytes do PDF."""
    url = (
        f"{settings.anvisa_base_url}"
        f"/api/consulta/medicamentos/arquivo/bula/parecer/{id_bula}/"
    )
    # A API exige Authorization como query param no endpoint de download
    params = {"Authorization": ""}

    close_client = client is None
    if client is None:
        client = criar_session()

    try:
        logger.debug("Baixando PDF id=%s", id_bula)
        response = client.get(url, params=params, headers=_HEADERS_EXTRAS, timeout=60)
        _verificar_bloqueio(response)
        response.raise_for_status()

        content_type = response.headers.get("content-type", "").split(";")[0].strip()
        if content_type not in _PDF_CONTENT_TYPES:
            raise ValueError(
                f"Esperado PDF, recebido Content-Type='{content_type}' para id={id_bula}"
            )

        return response.content

    finally:
        if close_client:
            client.close()
