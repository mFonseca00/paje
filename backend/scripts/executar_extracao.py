"""Runner da pipeline de extração LLM em lote.

Uso:
    # Processa todas as bulas PENDENTES
    python backend/scripts/executar_extracao.py

    # Processa no máximo 5 bulas (útil para testes)
    python backend/scripts/executar_extracao.py --limite 5

    # Inclui bulas com status ERRO no reprocessamento
    python backend/scripts/executar_extracao.py --reprocessar-erro

    # Combinado
    python backend/scripts/executar_extracao.py --limite 10 --reprocessar-erro
"""
import argparse
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from backend.config import settings
from backend.extracao.pipeline import ResultadoExtracao, executar_extracao


def main() -> None:
    parser = argparse.ArgumentParser(description="Extração LLM em lote de bulas PENDENTES.")
    parser.add_argument(
        "--limite",
        type=int,
        default=None,
        metavar="N",
        help="Processa no máximo N bulas (padrão: todas as PENDENTES)",
    )
    parser.add_argument(
        "--reprocessar-erro",
        action="store_true",
        help="Inclui bulas com status ERRO além das PENDENTES",
    )
    args = parser.parse_args()

    print(f"Provider: {settings.llm_provider}  |  Modelo: {settings.llm_model}")
    if args.limite:
        print(f"Limite: {args.limite} bula(s)")
    if args.reprocessar_erro:
        print("Reprocessando bulas com ERRO também.")
    print()

    resumo = executar_extracao(
        limite=args.limite,
        reprocessar_erro=args.reprocessar_erro,
    )

    print(f"\n{'='*50}")
    print(f"Extração concluída")
    print(f"{'='*50}")
    print(f"Total processado:   {resumo.total}")
    print(f"  PROCESSADO:       {resumo.processados}")
    print(f"  ERRO:             {resumo.erros}")
    print(f"  Sem arquivo:      {resumo.sem_arquivo}")

    if resumo.erros > 0:
        print("\nBulas com ERRO:")
        for log in resumo.logs:
            if log.resultado == ResultadoExtracao.ERRO:
                print(f"  bula_id={log.bula_id} | {log.id_bula_anvisa[:30]}... | {log.detalhe}")

    if resumo.sem_arquivo > 0:
        print("\nBulas sem arquivo markdown/PDF:")
        for log in resumo.logs:
            if log.resultado in (ResultadoExtracao.SEM_MARKDOWN, ResultadoExtracao.SEM_PDF):
                print(f"  bula_id={log.bula_id} | {log.resultado} | {log.detalhe}")


if __name__ == "__main__":
    main()
