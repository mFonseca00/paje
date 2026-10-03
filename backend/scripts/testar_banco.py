"""
Smoke-test do banco de dados.

Uso:
    python backend/scripts/testar_banco.py

Insere um medicamento, uma bula, uma contra-indicação e uma interação,
faz consultas e imprime os resultados para validação manual.
Limpa os dados de teste ao final.
"""
import sys

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


from backend.armazenamento.repositorio import (
    atualizar_status_bula,
    buscar_bula_por_id_anvisa,
    buscar_medicamento_por_nome,
    criar_bula,
    criar_contraindicacao,
    criar_interacao,
    criar_medicamento,
    get_session,
    listar_bulas_por_status,
    listar_contraindicacoes_por_bula,
    listar_interacoes_por_bula,
    listar_medicamentos,
)
from backend.armazenamento.modelos import StatusProcessamento


def separador(titulo: str) -> None:
    print(f"\n{'='*50}")
    print(f"  {titulo}")
    print("="*50)


def main() -> None:
    session = get_session()

    separador("1. Criando medicamento de teste")
    med = criar_medicamento(session, nome_comercial="DIPIRONA_TESTE", substancia_ativa="Metamizol sódico")
    session.commit()
    print(f"  Medicamento criado: id={med.id}, nome={med.nome_comercial}")

    separador("2. Criando bula com status PENDENTE")
    bula = criar_bula(session, medicamento_id=med.id, id_bula_anvisa="TESTE_001", caminho_pdf="docs/bulas/teste.pdf")
    session.commit()
    print(f"  Bula criada: id={bula.id}, status={bula.status_processamento_ia.value}")

    separador("3. Consultando bulas PENDENTE")
    pendentes = listar_bulas_por_status(session, StatusProcessamento.PENDENTE)
    print(f"  Bulas PENDENTE: {[b.id_bula_anvisa for b in pendentes]}")

    separador("4. Adicionando contra-indicação e interação")
    ci = criar_contraindicacao(session, bula_id=bula.id, texto="Hipersensibilidade ao metamizol")
    inter = criar_interacao(session, bula_id=bula.id, substancia="Varfarina", efeito="Aumento do efeito anticoagulante")
    session.commit()
    print(f"  Contra-indicação: id={ci.id}")
    print(f"  Interação: id={inter.id}, substancia={inter.substancia}")

    separador("5. Avançando bula para PROCESSADO")
    atualizar_status_bula(
        session,
        bula_id=bula.id,
        status=StatusProcessamento.PROCESSADO,
        resposta_bruta={"modelo": "teste", "contraindicacoes": ["hipersensibilidade"]},
        versao_prompt="v1",
    )
    session.commit()
    bula_atualizada = buscar_bula_por_id_anvisa(session, "TESTE_001")
    print(f"  Status atualizado: {bula_atualizada.status_processamento_ia.value}")
    print(f"  Resposta bruta: {bula_atualizada.resposta_bruta_modelo}")

    separador("6. Consultando CI e interações da bula")
    cis = listar_contraindicacoes_por_bula(session, bula.id)
    inters = listar_interacoes_por_bula(session, bula.id)
    print(f"  Contra-indicações: {[c.texto for c in cis]}")
    print(f"  Interações: {[(i.substancia, i.efeito) for i in inters]}")

    separador("7. Listando todos os medicamentos")
    todos = listar_medicamentos(session)
    print(f"  Total de medicamentos: {len(todos)}")
    print(f"  Nomes: {[m.nome_comercial for m in todos]}")

    separador("8. Limpando dados de teste")
    for i in inters:
        session.delete(i)
    for c in cis:
        session.delete(c)
    session.delete(bula_atualizada)
    session.delete(med)
    session.commit()
    print("  Dados de teste removidos com sucesso.")

    session.close()
    print("\n✓ Smoke-test concluído — banco operacional.\n")


if __name__ == "__main__":
    main()
