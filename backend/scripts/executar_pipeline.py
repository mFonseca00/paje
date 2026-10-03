"""Pipeline unificado: aquisição → preprocessamento → extração.

Executa as etapas em sequência conforme configurado em .env.
Cada etapa pode ser desabilitada via variável PIPELINE_*_HABILITADA.

Uso:
    python backend/scripts/executar_pipeline.py
    python backend/scripts/executar_pipeline.py --limite 10
    python backend/scripts/executar_pipeline.py --limite 5 --reprocessar-erro
    python backend/scripts/executar_pipeline.py --ajuda
"""
import argparse
import logging
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from backend.config import settings
from backend.extracao.pipeline import ResultadoExtracao, executar_extracao, executar_preprocessamento_lote

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)

logger = logging.getLogger(__name__)


def _secao(titulo: str) -> None:
    print()
    print("=" * 60)
    print(titulo)
    print("=" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Pipeline unificado: aquisicao > preprocessamento > extracao.",
        add_help=False,
    )
    parser.add_argument(
        "--limite", "-n", type=int, default=None, metavar="N",
        help="Processar no maximo N itens por etapa.",
    )
    parser.add_argument(
        "--reprocessar-erro", action="store_true",
        help="Reprocessar itens com status ERRO nas etapas de aquisicao e extracao.",
    )
    parser.add_argument(
        "--ajuda", "-h", action="help",
        help="Exibe esta mensagem e encerra.",
    )
    args = parser.parse_args()

    _secao("Pipeline Paje TCC")
    print(f"Provider LLM : {settings.llm_provider}  |  Modelo: {settings.llm_model}")
    print(f"LLM_NUM_CTX  : {settings.llm_num_ctx}")
    if args.limite:
        print(f"Limite       : {args.limite} item(s) por etapa")
    if args.reprocessar_erro:
        print("Reprocessar ERRO: ativado")

    inicio_total = time.monotonic()
    resultados: dict[str, object] = {}

    # ------------------------------------------------------------------
    # Etapa 1: Aquisição
    # ------------------------------------------------------------------
    if not settings.pipeline_aquisicao_habilitada:
        print("\n[ETAPA 1] Aquisicao desabilitada (PIPELINE_AQUISICAO_HABILITADA=false)")
    else:
        _secao("Etapa 1 — Aquisicao")
        from backend.aquisicao.fluxo import ResultadoAquisicao, executar_aquisicao

        inicio = time.monotonic()
        resumo_aq = executar_aquisicao(
            limite=args.limite,
            reprocessar_erro=args.reprocessar_erro,
        )
        elapsed = time.monotonic() - inicio
        resultados["aquisicao"] = resumo_aq

        print(f"  Total      : {resumo_aq.total}")
        print(f"  Baixados   : {resumo_aq.baixados}")
        print(f"  Skips      : {resumo_aq.skips}")
        print(f"  Erros      : {resumo_aq.erros}")
        print(f"  Tempo      : {elapsed:.1f}s")

        if resumo_aq.bloqueado:
            print()
            print("[ATENCAO] Bloqueio detectado na aquisicao. Aguarde e tente novamente.")

    # ------------------------------------------------------------------
    # Etapa 2: Preprocessamento
    # ------------------------------------------------------------------
    if not settings.pipeline_preprocessamento_habilitada:
        print("\n[ETAPA 2] Preprocessamento desabilitado (PIPELINE_PREPROCESSAMENTO_HABILITADA=false)")
    else:
        _secao("Etapa 2 — Preprocessamento")

        inicio = time.monotonic()
        resumo_pre = executar_preprocessamento_lote(limite=args.limite)
        elapsed = time.monotonic() - inicio
        resultados["preprocessamento"] = resumo_pre

        print(f"  Total      : {resumo_pre.total}")
        print(f"  Gerados    : {resumo_pre.gerados}")
        print(f"  Ja existiam: {resumo_pre.ja_existiam}")
        print(f"  Sem PDF    : {resumo_pre.sem_pdf}")
        print(f"  Erros      : {resumo_pre.erros}")
        print(f"  Tempo      : {elapsed:.1f}s")

    # ------------------------------------------------------------------
    # Etapa 3: Extração
    # ------------------------------------------------------------------
    if not settings.pipeline_extracao_habilitada:
        print("\n[ETAPA 3] Extracao desabilitada (PIPELINE_EXTRACAO_HABILITADA=false)")
    else:
        _secao("Etapa 3 — Extracao LLM")

        inicio = time.monotonic()
        resumo_ex = executar_extracao(
            limite=args.limite,
            reprocessar_erro=args.reprocessar_erro if args.reprocessar_erro else None,
        )
        elapsed = time.monotonic() - inicio
        resultados["extracao"] = resumo_ex

        print(f"  Total      : {resumo_ex.total}")
        print(f"  Processados: {resumo_ex.processados}")
        print(f"  Erros      : {resumo_ex.erros}")
        print(f"  Sem arquivo: {resumo_ex.sem_arquivo}")
        print(f"  Tempo      : {elapsed:.1f}s")

        if resumo_ex.erros > 0:
            print("\n  Bulas com ERRO:")
            for log in resumo_ex.logs:
                if log.resultado == ResultadoExtracao.ERRO:
                    print(f"    bula_id={log.bula_id} | {log.detalhe}")

    # ------------------------------------------------------------------
    # Resumo consolidado
    # ------------------------------------------------------------------
    _secao("Resumo consolidado")
    elapsed_total = time.monotonic() - inicio_total

    etapas_executadas = list(resultados.keys())
    if etapas_executadas:
        print(f"Etapas executadas: {', '.join(etapas_executadas)}")
    else:
        print("Nenhuma etapa executada (todas desabilitadas).")

    if "aquisicao" in resultados:
        r = resultados["aquisicao"]
        print(f"  Aquisicao   : {r.total} processados, {r.erros} erros")
    if "preprocessamento" in resultados:
        r = resultados["preprocessamento"]
        print(f"  Preprocess  : {r.gerados} gerados, {r.erros} erros")
    if "extracao" in resultados:
        r = resultados["extracao"]
        print(f"  Extracao    : {r.processados} OK, {r.erros} erros")

    print(f"\nTempo total: {elapsed_total:.1f}s")
    print()


if __name__ == "__main__":
    main()
