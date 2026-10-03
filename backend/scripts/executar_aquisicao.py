"""Executa a pipeline de aquisição de bulas da ANVISA.

Uso:
    python backend/scripts/executar_aquisicao.py
    python backend/scripts/executar_aquisicao.py --limite 10
    python backend/scripts/executar_aquisicao.py --limite 10 --reprocessar-erro
    python backend/scripts/executar_aquisicao.py --ajuda
"""
import argparse
import logging
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from backend.aquisicao.fluxo import ResultadoAquisicao, executar_aquisicao

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Aquisicao de bulas da RENAME a partir do bulario ANVISA.",
        add_help=False,
    )
    parser.add_argument(
        "--limite", "-n", type=int, default=None,
        help="Processar apenas os primeiros N medicamentos da RENAME.",
    )
    parser.add_argument(
        "--reprocessar-erro", action="store_true",
        help="Reprocessar bulas que estao com status ERRO (reutiliza PDF em disco).",
    )
    parser.add_argument(
        "--ajuda", "-h", action="help",
        help="Exibe esta mensagem e encerra.",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("Aquisicao de Bulas — Paje TCC")
    print("=" * 60)
    if args.limite:
        print(f"Modo parcial: primeiros {args.limite} medicamentos da RENAME")
    else:
        print("Modo completo: toda a RENAME")
    if args.reprocessar_erro:
        print("Reprocessamento de ERRO: ativado")
    print()

    inicio = time.monotonic()
    resumo = executar_aquisicao(
        limite=args.limite,
        reprocessar_erro=args.reprocessar_erro,
    )
    elapsed = time.monotonic() - inicio

    print()
    print("=" * 60)
    print("Resumo da aquisicao")
    print("=" * 60)
    print(f"  Total processados : {resumo.total}")
    print(f"  Baixados          : {resumo.baixados}")
    print(f"  Substituidos      : {resumo.substituidos}")
    print(f"  Reprocessados     : {resumo.reprocessados}")
    print(f"  Recuperados       : {resumo.recuperados}")
    print(f"  Skips (ja existem): {resumo.skips}")
    print(f"  Nao encontrados   : {resumo.nao_encontrados}")
    print(f"  Erros             : {resumo.erros}")
    print(f"  Tempo total       : {elapsed:.1f}s")

    if resumo.bloqueado:
        print()
        print("[ATENCAO] Bloqueio detectado — aquisicao interrompida.")
        print("Aguarde alguns minutos e execute novamente.")

    if resumo.erros:
        print()
        print("Medicamentos com erro:")
        for log in resumo.logs:
            if log.resultado == ResultadoAquisicao.ERRO:
                print(f"  - {log.nome}: {log.detalhe}")

    print()


if __name__ == "__main__":
    main()
