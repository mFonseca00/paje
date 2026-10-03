import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

# Seções numeradas do template ANVISA bula paciente a extrair por inteiro.
# Seção 3 = contraindicações ("QUANDO NÃO DEVO USAR?")
# Seção 4 = precauções + interações ("O QUE DEVO SABER ANTES?")
_SECOES_ALVO = frozenset({3, 4})

# Pontuação que indica fim de frase — linhas bold que terminem com isso são
# parágrafos, não subheadings.
_PONTUACAO_FIM_FRASE = (".", ":", "!", "?")


@dataclass
class ResultadoPreprocessamento:
    texto: str
    secoes_encontradas: list[str] = field(default_factory=list)
    markdown_bruto_usado: bool = False


def _normalizar_heading(linha: str) -> str:
    """Extrai e limpa o texto de uma linha de heading markdown (#... texto).

    Remove marcadores # iniciais, negrito (**), <mark> e superscripts HTML.
    """
    texto = linha.lstrip("#").strip()
    texto = texto.replace("**", "").replace("<mark>", "").replace("</mark>", "")
    while "<sup>" in texto:
        inicio = texto.index("<sup>")
        fim_tag = texto.find("</sup>", inicio)
        if fim_tag == -1:
            break
        texto = texto[:inicio] + texto[fim_tag + len("</sup>"):]
    return texto.strip()


def _numero_secao(texto_normalizado: str) -> int | None:
    """Retorna o número da seção se o texto começar com 'N.' (bula paciente).

    Exemplos: '3. QUANDO NÃO...' → 3; 'Interações medicamentosas' → None.
    """
    partes = texto_normalizado.split(".", 1)
    if len(partes) > 1 and partes[0].strip().isdigit():
        return int(partes[0].strip())
    return None


def _detectar_secao_bold(linha: str) -> tuple[int, str] | None:
    """Detecta marcadores de seção numerada em formato bold sem heading (#).

    Alguns PDFs produzem seções como **5. TÍTULO** (sem marcador #) em vez de
    ### **5. TÍTULO**. Esta função reconhece esse padrão para que o extrator
    possa usá-los como fronteiras de seção (idx_fim).

    Retorna (número, texto_normalizado) ou None.
    """
    stripped = linha.strip()
    if not stripped.startswith("**"):
        return None
    # Remove todos os ** para obter o texto limpo
    texto = stripped.replace("**", "").strip()
    num = _numero_secao(texto)
    if num is None:
        return None
    return (num, texto)


def _detectar_bold_subheading(linha: str) -> str | None:
    """Detecta subheadings dentro das seções extraídas em formato bold puro.

    Aplicado apenas dentro do bloco 3-4 já extraído (opção C): linhas que
    são inteiramente **texto** sem pontuação de fim de frase e sem marcadores
    de lista são subseções, não parágrafos.

    Retorna o texto limpo (sem **) ou None se a linha não for um subheading.
    """
    stripped = linha.strip()
    if not (stripped.startswith("**") and stripped.endswith("**")):
        return None
    texto = stripped[2:-2].strip()
    # Exclui strings vazias, itens de lista e parágrafos com fim de frase
    if not texto or texto.startswith("-") or texto.endswith(_PONTUACAO_FIM_FRASE):
        return None
    # Exclui seções numeradas (já tratadas como fronteiras, não subheadings)
    if _numero_secao(texto) is not None:
        return None
    return texto


def _reescrever_heading(texto_normalizado: str) -> str:
    """Normaliza o nível do heading: ## para seções numeradas, ### para demais."""
    prefixo = "##" if _numero_secao(texto_normalizado) is not None else "###"
    return f"{prefixo} {texto_normalizado}\n"


def extrair_secoes_relevantes(markdown: str) -> ResultadoPreprocessamento:
    """Extrai as seções 3 e 4 do formato bula paciente da ANVISA (chunkless).

    Identifica seções numeradas tanto em formato heading (#) quanto em formato
    bold puro (**N. título**), que ocorre em alguns PDFs. Captura o bloco
    inteiro de 3 até o início da seção 5, incluindo subseções não-numeradas.

    No bloco extraído:
    - Headings com # são normalizados: ## para numerados, ### para demais.
    - Linhas bold puras sem pontuação final são promovidas a ### (opção C).

    Retorna o markdown bruto completo quando nenhuma seção-alvo é encontrada.
    """
    linhas = markdown.splitlines(keepends=True)

    # Mapear seções numeradas (heading # ou bold puro): (índice, número, texto)
    headings_num: list[tuple[int, int, str]] = []
    for i, linha in enumerate(linhas):
        if linha.startswith("#"):
            texto = _normalizar_heading(linha)
            num = _numero_secao(texto)
            if num is not None:
                headings_num.append((i, num, texto))
        else:
            resultado = _detectar_secao_bold(linha)
            if resultado is not None:
                headings_num.append((i, resultado[0], resultado[1]))

    # Localizar bloco das seções-alvo e registrar seus títulos
    idx_inicio: int | None = None
    idx_fim: int = len(linhas)
    nomes: list[str] = []

    for idx, num, texto in headings_num:
        if num in _SECOES_ALVO:
            if idx_inicio is None:
                idx_inicio = idx
            nomes.append(texto)
        elif num > max(_SECOES_ALVO) and idx_inicio is not None:
            idx_fim = idx
            break

    if not nomes:
        return ResultadoPreprocessamento(
            texto=markdown,
            secoes_encontradas=[],
            markdown_bruto_usado=True,
        )

    # Extrair bloco e normalizar headings (# e bold puro)
    linhas_normalizadas: list[str] = []
    for linha in linhas[idx_inicio:idx_fim]:
        if linha.startswith("#"):
            texto_norm = _normalizar_heading(linha)
            linha = _reescrever_heading(texto_norm)
        else:
            sub = _detectar_bold_subheading(linha)
            if sub is not None:
                linha = f"### {sub}\n"
        linhas_normalizadas.append(linha)

    return ResultadoPreprocessamento(
        texto="".join(linhas_normalizadas).strip(),
        secoes_encontradas=nomes,
        markdown_bruto_usado=False,
    )


def preprocessar_bula(pdf_path: Path) -> ResultadoPreprocessamento:
    """Converte PDF para markdown e extrai as seções relevantes."""
    from backend.preprocessamento.conversor import converter_pdf_para_markdown

    markdown = converter_pdf_para_markdown(pdf_path)
    resultado = extrair_secoes_relevantes(markdown)

    if resultado.markdown_bruto_usado:
        logger.info(
            "[%s] Nenhuma seção relevante encontrada — markdown bruto encaminhado (%.1f KB)",
            pdf_path.name,
            len(resultado.texto) / 1024,
        )
    else:
        logger.info(
            "[%s] Seções extraídas: %s (%.1f KB)",
            pdf_path.name,
            ", ".join(resultado.secoes_encontradas),
            len(resultado.texto) / 1024,
        )

    return resultado
