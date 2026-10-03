"""Agente Pydantic AI para extração clínica de bulas.

Implementa:
- Seleção de provider (Ollama local ou APIs externas via LLM_PROVIDER).
- Tool consultar_secao_bula para acesso sob demanda ao markdown bruto.
- Carregamento do prompt versionado a partir de prompts/extracao_v1.md.
"""
import logging
import re
from dataclasses import dataclass
from pathlib import Path

from pydantic_ai import Agent, RunContext

from backend.config import settings
from backend.extracao.schemas import ExtracacaoClinica

logger = logging.getLogger(__name__)


@dataclass
class ContextoBula:
    """Dependências injetadas no agente durante a extração de uma bula."""
    caminho_bruto: Path


# ---------------------------------------------------------------------------
# Carregamento do prompt versionado
# ---------------------------------------------------------------------------

def _carregar_prompt(versao: str) -> str:
    caminho = Path(f"prompts/extracao_{versao}.md")
    if not caminho.exists():
        raise FileNotFoundError(f"Arquivo de prompt não encontrado: {caminho}")
    return caminho.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Seleção de modelo
# ---------------------------------------------------------------------------

def _aquecer_ollama(model_name: str, num_ctx: int) -> None:
    """Pré-carrega o modelo ollama com num_ctx correto via API nativa.

    O endpoint OpenAI-compat (/v1/chat/completions) do ollama ignora options.num_ctx
    no carregamento do modelo. A API nativa (/api/chat) lê o parâmetro corretamente.
    Esse warmup garante que o modelo esteja carregado na janela certa antes que
    pydantic-ai envie a primeira requisição de inferência.
    """
    import json
    import urllib.request

    base_url = settings.ollama_base_url.rstrip("/")
    body = json.dumps({
        "model": model_name,
        "messages": [],
        "options": {"num_ctx": num_ctx},
        "stream": False,
    }).encode()
    req = urllib.request.Request(
        f"{base_url}/api/chat",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            r.read()
        logger.info("Ollama aquecido: modelo=%s num_ctx=%d", model_name, num_ctx)
    except Exception as e:
        logger.warning("Warmup ollama falhou (continuando mesmo assim): %s", e)


def _criar_modelo():
    provider = settings.llm_provider.lower()

    if provider == "ollama":
        from pydantic_ai.models.openai import OpenAIChatModel
        from pydantic_ai.providers.openai import OpenAIProvider
        from pydantic_ai.settings import ModelSettings

        # Ollama expõe API compatível com OpenAI em /v1
        ollama_provider = OpenAIProvider(
            base_url=f"{settings.ollama_base_url}/v1",
            api_key="ollama",
        )
        # extra_body com options.num_ctx é enviado no body de cada requisição,
        # mas ollama 0.17 ignora num_ctx no endpoint OpenAI-compat (/v1/chat/completions).
        # O warmup via API nativa (/api/chat) força o carregamento com num_ctx correto;
        # as requisições subsequentes usam o modelo já carregado na janela ampliada.
        _aquecer_ollama(settings.llm_model, settings.llm_num_ctx)
        model_settings = ModelSettings(extra_body={"options": {"num_ctx": settings.llm_num_ctx}})
        return OpenAIChatModel(settings.llm_model, provider=ollama_provider, settings=model_settings)

    if provider == "anthropic":
        from pydantic_ai.models.anthropic import AnthropicModel
        from pydantic_ai.providers.anthropic import AnthropicProvider

        anthropic_provider = AnthropicProvider(api_key=settings.anthropic_api_key)
        return AnthropicModel(settings.llm_model, provider=anthropic_provider)

    if provider == "openai":
        from pydantic_ai.models.openai import OpenAIChatModel
        from pydantic_ai.providers.openai import OpenAIProvider

        openai_provider = OpenAIProvider(api_key=settings.openai_api_key)
        return OpenAIChatModel(settings.llm_model, provider=openai_provider)

    if provider == "gemini":
        from pydantic_ai.models.google import GoogleModel
        from pydantic_ai.providers.google import GoogleProvider

        google_provider = GoogleProvider(api_key=settings.gemini_api_key)
        return GoogleModel(settings.llm_model, provider=google_provider)

    raise ValueError(
        f"LLM_PROVIDER '{settings.llm_provider}' não suportado. "
        "Use: ollama, anthropic, openai ou gemini."
    )


# ---------------------------------------------------------------------------
# Tool: busca de seção no markdown bruto
# ---------------------------------------------------------------------------

def _buscar_secao(markdown: str, referencia: str) -> str | None:
    """Localiza e retorna o conteúdo de uma seção no markdown.

    Aceita referências como '4.5', 'seção 4.5', 'item 4.3', '7', etc.
    Faz correspondência case-insensitive pelo número ou título da seção.
    """
    num_match = re.search(r"[\d]+(?:\.[\d]+)*", referencia)
    num_ref = num_match.group() if num_match else None

    linhas = markdown.splitlines(keepends=True)
    secoes: list[tuple[int, str]] = []  # (linha_inicio, titulo_normalizado)

    for i, linha in enumerate(linhas):
        if linha.startswith("#"):
            titulo = linha.lstrip("#").strip().lower()
            secoes.append((i, titulo))

    ref_texto = re.sub(r"[\d\.\s]+", "", referencia).strip().lower()

    idx_alvo: int | None = None
    for i, (pos, titulo) in enumerate(secoes):
        if num_ref and re.match(r"^" + re.escape(num_ref) + r"[\s\.\-]", titulo):
            idx_alvo = i
            break
        if ref_texto and ref_texto in titulo:
            idx_alvo = i
            break

    if idx_alvo is None:
        return None

    pos_inicio = secoes[idx_alvo][0]
    pos_fim = secoes[idx_alvo + 1][0] if idx_alvo + 1 < len(secoes) else len(linhas)

    return "".join(linhas[pos_inicio:pos_fim]).strip()


# ---------------------------------------------------------------------------
# Singleton do agente (inicialização lazy na primeira chamada de extrair_bula)
# ---------------------------------------------------------------------------

_agente: Agent[ContextoBula, ExtracacaoClinica] | None = None


def _construir_agente() -> Agent[ContextoBula, ExtracacaoClinica]:
    sistema = _carregar_prompt(settings.prompt_version)
    modelo = _criar_modelo()

    ag: Agent[ContextoBula, ExtracacaoClinica] = Agent(
        modelo,
        output_type=ExtracacaoClinica,
        deps_type=ContextoBula,
        system_prompt=sistema,
        retries=settings.llm_max_result_retries,
    )

    @ag.tool
    def consultar_secao_bula(ctx: RunContext[ContextoBula], referencia: str) -> str:
        """Retorna o conteúdo da seção referenciada a partir do markdown bruto da bula.

        Use esta tool quando o texto das seções 3 e 4 mencionar explicitamente outra
        seção como fonte de informação clínica (ex: 'ver item 4.5', 'conforme seção 7').
        Passe a referência identificada (ex: '4.5', '7', 'seção 4.3').
        """
        caminho = ctx.deps.caminho_bruto
        if not caminho.exists():
            return f"[Arquivo __bruto.md não encontrado: {caminho}]"

        markdown = caminho.read_text(encoding="utf-8")
        conteudo = _buscar_secao(markdown, referencia)
        if conteudo is None:
            return f"[Seção '{referencia}' não encontrada no markdown bruto]"
        return conteudo

    return ag


def _get_agente() -> Agent[ContextoBula, ExtracacaoClinica]:
    # Não é thread-safe: singleton por processo, adequado para execução síncrona.
    global _agente
    if _agente is None:
        _agente = _construir_agente()
    return _agente


# ---------------------------------------------------------------------------
# Função de extração síncrona
# ---------------------------------------------------------------------------

def extrair_bula(caminho_secoes: Path, caminho_bruto: Path) -> ExtracacaoClinica:
    """Executa a extração clínica de uma bula via agente LLM; propaga exceções ao chamador."""
    texto_secoes = caminho_secoes.read_text(encoding="utf-8")
    deps = ContextoBula(caminho_bruto=caminho_bruto)

    resultado = _get_agente().run_sync(texto_secoes, deps=deps)
    return resultado.output
