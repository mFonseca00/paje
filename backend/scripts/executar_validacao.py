"""Script standalone de validação da extração LLM.

Lê PDFs de docs/validacao/pdfs/, aplica o pipeline de extração (sem banco),
compara com o gabarito em docs/validacao/referencia_validacao.xlsx e grava
resultados em docs/validacao/resultados/{data}_{prompt_versao}_{modelo}/.

Uso:
    python backend/scripts/executar_validacao.py
"""
import logging
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)

from backend.config import settings
from backend.validacao.runner import executar_validacao


def main() -> None:
    print(f"Provider: {settings.llm_provider}  |  Modelo: {settings.llm_model}")
    print(f"Prompt: {settings.prompt_version}")
    print()

    pasta = executar_validacao()

    import json
    relatorio_path = pasta / "relatorio.json"
    relatorio = json.loads(relatorio_path.read_text(encoding="utf-8"))

    ci = relatorio["contraindicacoes"]
    im = relatorio["interacoes"]

    print(f"\n{'='*60}")
    print(f"Validação concluída — {relatorio['total_bulas']} bulas")
    print(f"{'='*60}")
    print(f"\nContra-indicações:")
    print(f"  Precisão:  {ci['precisao']:.4f}")
    print(f"  Revocação: {ci['revocacao']:.4f}")
    print(f"  F2:        {ci['f2']:.4f}")
    print(f"  TP/FP/FN:  {ci['verdadeiro_positivo (tp)']}/{ci['falso_positivo (fp)']}/{ci['falso_negativo (fn)']}")
    print(f"  Aprovado:  {'SIM' if ci['aprovado'] else 'NÃO'}")
    print(f"\nInterações medicamentosas:")
    print(f"  Precisão:  {im['precisao']:.4f}")
    print(f"  Revocação: {im['revocacao']:.4f}")
    print(f"  F2:        {im['f2']:.4f}")
    print(f"  TP/FP/FN:  {im['verdadeiro_positivo (tp)']}/{im['falso_positivo (fp)']}/{im['falso_negativo (fn)']}")
    print(f"  Aprovado:  {'SIM' if im['aprovado'] else 'NÃO'}")
    print(f"\nAprovado geral: {'SIM' if relatorio['aprovado_geral'] else 'NÃO'}")
    print(f"\nResultados em: {pasta}")


if __name__ == "__main__":
    main()
