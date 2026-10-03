"""Testa a busca de 3 medicamentos no bulario ANVISA e exibe a resposta.

Uso:
    python backend/scripts/testar_busca.py
"""
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from backend.aquisicao.cliente import BloqueioAnvisaError, buscar_bulas, criar_session
from backend.config import settings

MEDICAMENTOS_TESTE = ["dipirona", "amoxicilina", "metformina"]


def main() -> None:
    print(f"Base URL: {settings.anvisa_base_url}")
    print(f"Delay entre requisicoes: {settings.anvisa_delay_segundos}s")
    print("-" * 60)

    with criar_session() as client:
        for nome in MEDICAMENTOS_TESTE:
            print(f"\nBuscando: '{nome}'")
            try:
                resultados = buscar_bulas(nome, client=client)
                if not resultados:
                    print("  -> Nenhum resultado encontrado.")
                else:
                    print(f"  -> {len(resultados)} resultado(s):")
                    for r in resultados[:3]:
                        print(f"     nome_produto   : {r.nome_produto}")
                        print(f"     id_bula_paciente    : {r.id_bula_paciente}")
                        print(f"     id_bula_profissional: {r.id_bula_profissional}")
                        print(f"     expediente     : {r.expediente}")
                        print()
            except BloqueioAnvisaError as e:
                print(f"  [BLOQUEIO] {e}")
                print("  Interrompendo — aguarde antes de tentar novamente.")
                break
            except Exception as e:
                print(f"  [ERRO] {type(e).__name__}: {e}")

            time.sleep(settings.anvisa_delay_segundos)

    print("-" * 60)
    print("Teste concluido.")


if __name__ == "__main__":
    main()
