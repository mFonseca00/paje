"""Converte PDFs de bulas para markdown e salva em disco para inspeção manual.

Uso:
    # Converte todos os PDFs em docs/bulas/ e salva em docs/markdown_bulas/
    python backend/scripts/testar_preprocessamento.py

    # Converte um PDF específico
    python backend/scripts/testar_preprocessamento.py docs/bulas/aciclovir.pdf

    # Define outro diretório de saída
    python backend/scripts/testar_preprocessamento.py --saida outro/dir

    # Combinado
    python backend/scripts/testar_preprocessamento.py docs/bulas/aciclovir.pdf --saida outro/dir
"""
import argparse
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from backend.preprocessamento.conversor import converter_pdf_para_markdown
from backend.preprocessamento.extrator import extrair_secoes_relevantes


def processar(pdf_path: Path, saida_dir: Path) -> None:
    print(f"  Convertendo: {pdf_path.name} ...", end=" ", flush=True)

    markdown = converter_pdf_para_markdown(pdf_path)
    resultado = extrair_secoes_relevantes(markdown)

    # Salva o markdown bruto completo
    arquivo_bruto = saida_dir / f"{pdf_path.stem}__bruto.md"
    arquivo_bruto.write_text(markdown, encoding="utf-8")

    # Salva apenas as seções extraídas
    arquivo_secoes = saida_dir / f"{pdf_path.stem}__secoes.md"
    arquivo_secoes.write_text(resultado.texto, encoding="utf-8")

    if resultado.markdown_bruto_usado:
        print(f"AVISO — nenhuma seção encontrada ({len(markdown) / 1024:.1f} KB bruto)")
    else:
        secoes = ", ".join(resultado.secoes_encontradas)
        print(f"OK — {len(resultado.secoes_encontradas)} seção(ões): {secoes} ({len(resultado.texto) / 1024:.1f} KB)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Converte PDFs de bulas para markdown.")
    parser.add_argument("pdf", nargs="?", help="PDF específico a converter (opcional)")
    parser.add_argument("--saida", default="docs/markdown_bulas", help="Diretório de saída (padrão: docs/markdown_bulas)")
    args = parser.parse_args()

    saida_dir = Path(args.saida)
    saida_dir.mkdir(parents=True, exist_ok=True)

    if args.pdf:
        pdfs = [Path(args.pdf)]
        if not pdfs[0].exists():
            print(f"Arquivo não encontrado: {pdfs[0]}")
            sys.exit(1)
    else:
        pdfs = sorted(Path("docs/bulas").glob("*.pdf"))
        if not pdfs:
            print("Nenhum PDF encontrado em docs/bulas/.")
            sys.exit(1)

    print(f"Saída: {saida_dir.resolve()}")
    print(f"PDFs a processar: {len(pdfs)}\n")

    for pdf in pdfs:
        processar(pdf, saida_dir)

    print(f"\nConcluído. Arquivos salvos em: {saida_dir.resolve()}")
    print("  *__bruto.md   → markdown completo do PDF")
    print("  *__secoes.md  → apenas as seções extraídas")


if __name__ == "__main__":
    main()
