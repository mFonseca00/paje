import pytest

from backend.armazenamento.modelos import StatusProcessamento
from backend.armazenamento.repositorio import (
    atualizar_status_bula,
    buscar_bula_por_id_anvisa,
    buscar_medicamento_por_nome,
    criar_bula,
    criar_contraindicacao,
    criar_interacao,
    criar_medicamento,
    listar_bulas_por_status,
    listar_contraindicacoes_por_bula,
    listar_interacoes_por_bula,
    listar_medicamentos,
)


class TestMedicamentos:
    def test_criar_e_buscar_medicamento(self, session):
        med = criar_medicamento(session, nome_comercial="Amoxicilina", substancia_ativa="Amoxicilina tri-hidratada")
        session.commit()

        encontrado = buscar_medicamento_por_nome(session, "Amoxicilina")
        assert encontrado is not None
        assert encontrado.substancia_ativa == "Amoxicilina tri-hidratada"

    def test_buscar_medicamento_inexistente_retorna_none(self, session):
        resultado = buscar_medicamento_por_nome(session, "NAO_EXISTE_XYZ")
        assert resultado is None

    def test_listar_medicamentos(self, session):
        criar_medicamento(session, nome_comercial="Med_A")
        criar_medicamento(session, nome_comercial="Med_B")
        session.commit()

        todos = listar_medicamentos(session)
        nomes = [m.nome_comercial for m in todos]
        assert "Med_A" in nomes
        assert "Med_B" in nomes

    def test_criar_medicamento_com_nome_dcb(self, session):
        med = criar_medicamento(session, nome_comercial="ORENCIA", nome_dcb="abatacepte")
        session.commit()

        assert med.nome_comercial == "ORENCIA"
        assert med.nome_dcb == "abatacepte"

    def test_criar_medicamento_sem_nome_dcb(self, session):
        med = criar_medicamento(session, nome_comercial="dipirona")
        session.commit()

        assert med.nome_dcb is None

    def test_buscar_por_nome_comercial(self, session):
        criar_medicamento(session, nome_comercial="ORENCIA", nome_dcb="abatacepte")
        session.commit()

        encontrado = buscar_medicamento_por_nome(session, "ORENCIA")
        assert encontrado is not None
        assert encontrado.nome_dcb == "abatacepte"

    def test_buscar_por_nome_dcb(self, session):
        criar_medicamento(session, nome_comercial="ORENCIA", nome_dcb="abatacepte")
        session.commit()

        encontrado = buscar_medicamento_por_nome(session, "abatacepte")
        assert encontrado is not None
        assert encontrado.nome_comercial == "ORENCIA"

    def test_buscar_por_nome_dcb_sem_fallback_nao_duplica(self, session):
        """Busca pelo DCB deve encontrar o mesmo registro, não criar duplicata."""
        med = criar_medicamento(session, nome_comercial="ORENCIA", nome_dcb="abatacepte")
        session.commit()

        por_comercial = buscar_medicamento_por_nome(session, "ORENCIA")
        por_dcb = buscar_medicamento_por_nome(session, "abatacepte")
        assert por_comercial.id == por_dcb.id == med.id


class TestBulas:
    def test_criar_bula_com_status_pendente(self, session):
        med = criar_medicamento(session, nome_comercial="Ibuprofeno")
        session.commit()

        bula = criar_bula(session, medicamento_id=med.id, id_bula_anvisa="IBUP_001")
        session.commit()

        assert bula.status_processamento_ia == StatusProcessamento.PENDENTE
        assert bula.caminho_pdf is None

    def test_buscar_bula_por_id_anvisa(self, session):
        med = criar_medicamento(session, nome_comercial="Paracetamol")
        session.commit()
        criar_bula(session, medicamento_id=med.id, id_bula_anvisa="PARA_001", caminho_pdf="docs/bulas/para.pdf")
        session.commit()

        bula = buscar_bula_por_id_anvisa(session, "PARA_001")
        assert bula is not None
        assert bula.caminho_pdf == "docs/bulas/para.pdf"

    def test_buscar_bula_inexistente_retorna_none(self, session):
        assert buscar_bula_por_id_anvisa(session, "ID_INEXISTENTE") is None

    def test_listar_bulas_por_status(self, session):
        med = criar_medicamento(session, nome_comercial="Atenolol")
        session.commit()
        b1 = criar_bula(session, medicamento_id=med.id, id_bula_anvisa="ATEN_001")
        b2 = criar_bula(session, medicamento_id=med.id, id_bula_anvisa="ATEN_002")
        session.commit()

        atualizar_status_bula(session, b2.id, StatusProcessamento.PROCESSADO)
        session.commit()

        pendentes = listar_bulas_por_status(session, StatusProcessamento.PENDENTE)
        processados = listar_bulas_por_status(session, StatusProcessamento.PROCESSADO)

        assert any(b.id_bula_anvisa == "ATEN_001" for b in pendentes)
        assert any(b.id_bula_anvisa == "ATEN_002" for b in processados)

    def test_atualizar_status_para_erro_com_resposta_bruta(self, session):
        med = criar_medicamento(session, nome_comercial="Metformina")
        session.commit()
        bula = criar_bula(session, medicamento_id=med.id, id_bula_anvisa="MET_001")
        session.commit()

        resposta = {"erro": "JSON inválido retornado pelo modelo"}
        atualizar_status_bula(
            session, bula.id, StatusProcessamento.ERRO, resposta_bruta=resposta
        )
        session.commit()

        bula_atualizada = buscar_bula_por_id_anvisa(session, "MET_001")
        assert bula_atualizada.status_processamento_ia == StatusProcessamento.ERRO
        assert bula_atualizada.resposta_bruta_modelo["erro"] == "JSON inválido retornado pelo modelo"

    def test_atualizar_status_com_versao_prompt(self, session):
        med = criar_medicamento(session, nome_comercial="Losartana")
        session.commit()
        bula = criar_bula(session, medicamento_id=med.id, id_bula_anvisa="LOS_001")
        session.commit()

        atualizar_status_bula(
            session, bula.id, StatusProcessamento.PROCESSADO,
            resposta_bruta={"ok": True}, versao_prompt="v1"
        )
        session.commit()

        bula_atualizada = buscar_bula_por_id_anvisa(session, "LOS_001")
        assert bula_atualizada.versao_prompt == "v1"


class TestContraindicacoes:
    def test_criar_e_listar_contraindicacoes(self, session):
        med = criar_medicamento(session, nome_comercial="Captopril")
        session.commit()
        bula = criar_bula(session, medicamento_id=med.id, id_bula_anvisa="CAP_001")
        session.commit()

        criar_contraindicacao(session, bula_id=bula.id, texto="Hipersensibilidade ao captopril")
        criar_contraindicacao(session, bula_id=bula.id, texto="Angioedema hereditário")
        session.commit()

        cis = listar_contraindicacoes_por_bula(session, bula.id)
        assert len(cis) == 2
        textos = [c.texto for c in cis]
        assert "Hipersensibilidade ao captopril" in textos

    def test_bula_sem_contraindicacoes_retorna_lista_vazia(self, session):
        med = criar_medicamento(session, nome_comercial="Sinvastatina")
        session.commit()
        bula = criar_bula(session, medicamento_id=med.id, id_bula_anvisa="SIN_001")
        session.commit()

        cis = listar_contraindicacoes_por_bula(session, bula.id)
        assert cis == []


class TestInteracoes:
    def test_criar_e_listar_interacoes(self, session):
        med = criar_medicamento(session, nome_comercial="Varfarina")
        session.commit()
        bula = criar_bula(session, medicamento_id=med.id, id_bula_anvisa="VAR_001")
        session.commit()

        criar_interacao(session, bula_id=bula.id, substancia="AAS", efeito="Aumento do risco de sangramento")
        criar_interacao(session, bula_id=bula.id, substancia="Amiodarona", efeito="Potencialização do efeito anticoagulante")
        session.commit()

        inters = listar_interacoes_por_bula(session, bula.id)
        assert len(inters) == 2
        substancias = [i.substancia for i in inters]
        assert "AAS" in substancias
        assert "Amiodarona" in substancias
