"""Testa a extração clínica em uma única bula e salva o JSON resultante.

Uso:
    # Processa pelo caminho do PDF (gera markdown se necessário)
    python backend/scripts/testar_extracao.py docs/bulas/paciente__dipirona__abc.pdf

    # Processa diretamente pelo arquivo __secoes.md já existente
    python backend/scripts/testar_extracao.py --secoes docs/markdown_bulas/paciente__dipirona__abc__secoes.md

    # Define diretório de saída (padrão: output/)
    python backend/scripts/testar_extracao.py docs/bulas/xyz.pdf --saida output/

    # Usa modelo diferente via flags de ambiente
    LLM_PROVIDER=anthropic LLM_MODEL=claude-3-haiku-20240307 python backend/scripts/testar_extracao.py ...
"""
import argparse
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from backend.extracao.agente import extrair_bula
from backend.preprocessamento.conversor import converter_pdf_para_markdown
from backend.preprocessamento.extrator import extrair_secoes_relevantes


def _derivar_caminhos_markdown(pdf_path: Path, markdown_dir: Path) -> tuple[Path, Path]:
    stem = pdf_path.stem
    return (
        markdown_dir / f"{stem}__secoes.md",
        markdown_dir / f"{stem}__bruto.md",
    )


def _gerar_markdown_se_necessario(pdf_path: Path, markdown_dir: Path) -> tuple[Path, Path]:
    caminho_secoes, caminho_bruto = _derivar_caminhos_markdown(pdf_path, markdown_dir)
    markdown_dir.mkdir(parents=True, exist_ok=True)

    if not caminho_bruto.exists() or not caminho_secoes.exists():
        print(f"  Convertendo PDF → markdown: {pdf_path.name} ...", end=" ", flush=True)
        markdown = converter_pdf_para_markdown(pdf_path)
        resultado = extrair_secoes_relevantes(markdown)
        caminho_bruto.write_text(markdown, encoding="utf-8")
        caminho_secoes.write_text(resultado.texto, encoding="utf-8")
        print("OK")
    else:
        print(f"  Usando markdown existente: {caminho_secoes.name}")

    return caminho_secoes, caminho_bruto


def processar(caminho_secoes: Path, caminho_bruto: Path, saida_dir: Path) -> None:
    nome_base = caminho_secoes.stem.replace("__secoes", "")
    arquivo_saida = saida_dir / f"{nome_base}_extracao.json"

    print(f"\n  Extraindo: {caminho_secoes.name}")
    print(f"  Provider: {__import__('backend.config', fromlist=['settings']).settings.llm_provider}")
    print(f"  Modelo:   {__import__('backend.config', fromlist=['settings']).settings.llm_model}")
    print("  Aguardando resposta do modelo...", end=" ", flush=True)

    try:
        resultado = extrair_bula(caminho_secoes, caminho_bruto)
    except Exception as e:
        print(f"\n  ERRO: {e}")
        sys.exit(1)

    print("OK")

    saida_dir.mkdir(parents=True, exist_ok=True)
    dados = resultado.model_dump()
    arquivo_saida.write_text(
        json.dumps(dados, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"\n  Contra-indicações extraídas: {len(resultado.contraindicacoes)}")
    print(f"  Interações extraídas:        {len(resultado.interacoes)}")
    print(f"  JSON salvo em: {arquivo_saida.resolve()}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Testa extração LLM em uma única bula.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("pdf", nargs="?", help="Caminho do PDF da bula")
    group.add_argument("--secoes", help="Caminho do arquivo __secoes.md já existente")
    parser.add_argument("--saida", default="output", help="Diretório de saída (padrão: output/)")
    parser.add_argument("--markdown-dir", default="docs/markdown_bulas",
                        help="Diretório dos markdowns (padrão: docs/markdown_bulas/)")
    args = parser.parse_args()

    saida_dir = Path(args.saida)

    if args.secoes:
        caminho_secoes = Path(args.secoes)
        if not caminho_secoes.exists():
            print(f"Arquivo não encontrado: {caminho_secoes}")
            sys.exit(1)
        stem_base = caminho_secoes.stem.replace("__secoes", "")
        caminho_bruto = caminho_secoes.parent / f"{stem_base}__bruto.md"
        if not caminho_bruto.exists():
            print(f"Arquivo __bruto.md não encontrado: {caminho_bruto}")
            sys.exit(1)
    else:
        pdf_path = Path(args.pdf)
        if not pdf_path.exists():
            print(f"PDF não encontrado: {pdf_path}")
            sys.exit(1)
        markdown_dir = Path(args.markdown_dir)
        caminho_secoes, caminho_bruto = _gerar_markdown_se_necessario(pdf_path, markdown_dir)

    processar(caminho_secoes, caminho_bruto, saida_dir)


if __name__ == "__main__":
    main()
