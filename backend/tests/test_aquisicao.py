"""Testes unitários para o módulo de aquisição.

Os testes fazem mock do cliente HTTP (httpx.Client) e do banco de dados
para cobrir os diferentes caminhos do fluxo sem dependências externas.
"""
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from backend.aquisicao.cliente import AcessoNegadoError, BloqueioAnvisaError, ErroTransitorioAnvisaError, ResultadoBusca, buscar_bulas, baixar_pdf
from backend.aquisicao.fluxo import (
    LogAquisicao,
    ResultadoAquisicao,
    _escolher_id_bula,
    _nome_arquivo,
    _selecionar_resultado,
    _adquirir,
    _buscar_fallback_nome_comercial,
    _com_retry,
)
from backend.aquisicao.rename import _normalizar, carregar_nomes_rename
from backend.armazenamento.modelos import StatusProcessamento


# ---------------------------------------------------------------------------
# Utilitários
# ---------------------------------------------------------------------------

class TestNormalizar:
    def test_remove_acentos(self):
        assert _normalizar("ácido acético") == "acido acetico"

    def test_lowercase(self):
        assert _normalizar("DIPIRONA") == "dipirona"

    def test_espacos_duplicados(self):
        assert _normalizar("  meta  formina  ") == "meta formina"

    def test_caracteres_especiais_unicode(self):
        assert _normalizar("cloreto de sódio") == "cloreto de sodio"


class TestSelecionarResultado:
    def _r(self, nome_produto, id_paciente="PAC", id_prof="PROF"):
        return ResultadoBusca(
            id_bula_paciente=id_paciente,
            id_bula_profissional=id_prof,
            nome_produto=nome_produto,
        )

    def test_lista_mista_retorna_simples(self):
        resultados = [
            self._r("amoxicilina + clavulanato de potassio"),
            self._r("amoxicilina"),
            self._r("amoxicilina 500mg"),
        ]
        escolhido = _selecionar_resultado("amoxicilina", resultados)
        assert escolhido.nome_produto == "amoxicilina"

    def test_lista_so_combinacoes_usa_fallback(self):
        resultados = [
            self._r("amoxicilina + clavulanato 875+125mg"),
            self._r("amoxicilina + sulbactam"),
        ]
        escolhido = _selecionar_resultado("amoxicilina", resultados)
        assert escolhido.nome_produto == "amoxicilina + clavulanato 875+125mg"

    def test_busca_com_mais_nao_filtra(self):
        resultados = [
            self._r("amoxicilina + clavulanato de potassio"),
            self._r("amoxicilina"),
        ]
        escolhido = _selecionar_resultado("amoxicilina + clavulanato de potassio", resultados)
        assert escolhido.nome_produto == "amoxicilina + clavulanato de potassio"

    def test_lista_vazia_retorna_none(self):
        assert _selecionar_resultado("amoxicilina", []) is None

    def test_todos_sem_id_retorna_none(self):
        resultados = [
            ResultadoBusca(id_bula_paciente=None, id_bula_profissional=None, nome_produto="amoxicilina"),
        ]
        assert _selecionar_resultado("amoxicilina", resultados) is None


class TestEscolherIdBula:
    def test_prefere_paciente_por_padrao(self):
        r = ResultadoBusca(
            id_bula_paciente="PAC001",
            id_bula_profissional="PROF001",
            nome_produto="Teste",
        )
        assert _escolher_id_bula(r) == "PAC001"

    def test_fallback_para_profissional_quando_paciente_ausente(self):
        r = ResultadoBusca(
            id_bula_paciente=None,
            id_bula_profissional="PROF001",
            nome_produto="Teste",
        )
        assert _escolher_id_bula(r) == "PROF001"

    def test_prefere_profissional_quando_configurado(self):
        from unittest.mock import patch
        r = ResultadoBusca(
            id_bula_paciente="PAC001",
            id_bula_profissional="PROF001",
            nome_produto="Teste",
        )
        with patch("backend.aquisicao.fluxo.settings") as mock_settings:
            mock_settings.anvisa_tipo_bula = "profissional"
            assert _escolher_id_bula(r) == "PROF001"

    def test_nenhum_disponivel(self):
        r = ResultadoBusca(
            id_bula_paciente=None,
            id_bula_profissional=None,
            nome_produto="Teste",
        )
        assert _escolher_id_bula(r) is None


class TestNomeArquivo:
    def _s(self, tipo="paciente"):
        m = MagicMock()
        m.anvisa_tipo_bula = tipo
        return m

    def test_formato_basico(self):
        with patch("backend.aquisicao.fluxo.settings", self._s()):
            nome = _nome_arquivo("dipirona", "ID123")
        assert nome == "paciente__dipirona__ID123.pdf"

    def test_caracteres_especiais_virao_underscore(self):
        with patch("backend.aquisicao.fluxo.settings", self._s()):
            nome = _nome_arquivo("acetato de abiraterona", "ID456")
        assert nome == "paciente__acetato_de_abiraterona__ID456.pdf"

    def test_nome_longo_sem_truncamento(self):
        nome_longo = "a" * 100
        with patch("backend.aquisicao.fluxo.settings", self._s()):
            nome = _nome_arquivo(nome_longo, "ID789")
        assert f"__{'a' * 100}__ID789.pdf" in nome

    def test_id_jwt_longo_usa_sufixo(self):
        jwt = "eyJhbGciOiJIUzUxMiJ9.eyJqdGkiOiIzNDc5MjI3OCJ9.assinatura_longa"
        with patch("backend.aquisicao.fluxo.settings", self._s()):
            nome = _nome_arquivo("aciclovir", jwt)
        assert nome.endswith(f"__{jwt[-8:]}.pdf")

    def test_sem_fallback_usa_apenas_nome_medicamento(self):
        with patch("backend.aquisicao.fluxo.settings", self._s()):
            nome = _nome_arquivo("dipirona", "ID123", nome_dcb="dipirona")
        assert nome == "paciente__dipirona__ID123.pdf"

    def test_com_fallback_inclui_dcb_antes_do_comercial(self):
        with patch("backend.aquisicao.fluxo.settings", self._s()):
            nome = _nome_arquivo("ORENCIA", "ID123", nome_dcb="abatacepte")
        assert nome == "paciente__abatacepte__ORENCIA__ID123.pdf"

    def test_com_fallback_tipo_profissional(self):
        with patch("backend.aquisicao.fluxo.settings", self._s("profissional")):
            nome = _nome_arquivo("AMOXIL", "ID999", nome_dcb="amoxicilina")
        assert nome == "profissional__amoxicilina__AMOXIL__ID999.pdf"


# ---------------------------------------------------------------------------
# Cliente HTTP (mock)
# ---------------------------------------------------------------------------

class TestBuscarBulas:
    def _mock_response(self, json_data: dict, status_code: int = 200):
        resp = MagicMock()
        resp.status_code = status_code
        resp.headers = {"content-type": "application/json"}
        resp.json.return_value = json_data
        resp.raise_for_status = MagicMock()
        resp.url = "https://consultas.anvisa.gov.br/api/consulta/bulario"
        return resp

    def test_retorna_resultados(self):
        client = MagicMock()
        client.get.return_value = self._mock_response({
            "content": [
                {
                    "nomeProduto": "DIPIRONA 500MG",
                    "idBulaProfissionalProtegido": "PROF001",
                    "idBulaPacienteProtegido": "PAC001",
                    "numExpediente": "EXP001",
                }
            ]
        })
        resultados = buscar_bulas("dipirona", client=client)
        assert len(resultados) == 1
        assert resultados[0].id_bula_profissional == "PROF001"
        assert resultados[0].nome_produto == "DIPIRONA 500MG"

    def test_vazio_retorna_lista_vazia(self):
        client = MagicMock()
        client.get.return_value = self._mock_response({"content": []})
        resultados = buscar_bulas("inexistente", client=client)
        assert resultados == []

    def test_status_403_lanca_acesso_negado(self):
        client = MagicMock()
        resp = MagicMock()
        resp.status_code = 403
        resp.headers = {"content-type": "application/json"}
        resp.text = "Forbidden"
        resp.url = "https://consultas.anvisa.gov.br/api/consulta/bulario"
        resp.request = MagicMock()
        resp.request.headers = {}
        client.get.return_value = resp
        with pytest.raises(AcessoNegadoError):
            buscar_bulas("dipirona", client=client)

    def test_status_429_lanca_bloqueio(self):
        client = MagicMock()
        resp = MagicMock()
        resp.status_code = 429
        resp.headers = {"content-type": "application/json"}
        resp.url = "https://consultas.anvisa.gov.br/api/consulta/bulario"
        client.get.return_value = resp
        with pytest.raises(BloqueioAnvisaError):
            buscar_bulas("dipirona", client=client)

    def test_html_inesperado_lanca_bloqueio(self):
        client = MagicMock()
        resp = MagicMock()
        resp.status_code = 200
        resp.headers = {"content-type": "text/html; charset=utf-8"}
        resp.url = "https://consultas.anvisa.gov.br/api/consulta/bulario"
        client.get.return_value = resp
        with pytest.raises(BloqueioAnvisaError):
            buscar_bulas("dipirona", client=client)


class TestBaixarPdf:
    def test_retorna_bytes_pdf(self):
        client = MagicMock()
        resp = MagicMock()
        resp.status_code = 200
        resp.headers = {"content-type": "application/pdf"}
        resp.content = b"%PDF-1.4 fake content"
        resp.raise_for_status = MagicMock()
        resp.url = "https://consultas.anvisa.gov.br/api/consulta/medicamentos/arquivo/bula/parecer/ID001/"
        client.get.return_value = resp
        conteudo = baixar_pdf("ID001", client=client)
        assert conteudo == b"%PDF-1.4 fake content"

    def test_aceita_force_download(self):
        client = MagicMock()
        resp = MagicMock()
        resp.status_code = 200
        resp.headers = {"content-type": "application/force-download"}
        resp.content = b"%PDF-1.4 force-download"
        resp.raise_for_status = MagicMock()
        resp.url = "https://consultas.anvisa.gov.br/api/consulta/medicamentos/arquivo/bula/parecer/ID001/"
        client.get.return_value = resp
        conteudo = baixar_pdf("ID001", client=client)
        assert conteudo == b"%PDF-1.4 force-download"

    def test_content_type_errado_lanca_erro(self):
        client = MagicMock()
        resp = MagicMock()
        resp.status_code = 200
        # HTML no endpoint de PDF é tratado como possível CAPTCHA/bloqueio
        resp.headers = {"content-type": "text/html"}
        resp.raise_for_status = MagicMock()
        resp.url = "https://consultas.anvisa.gov.br/api/consulta/medicamentos/arquivo/bula/parecer/ID001/"
        client.get.return_value = resp
        with pytest.raises(BloqueioAnvisaError):
            baixar_pdf("ID001", client=client)

    def test_content_type_json_lanca_valor_invalido(self):
        client = MagicMock()
        resp = MagicMock()
        resp.status_code = 200
        # JSON 200 OK não é bloqueio, mas também não é PDF
        resp.headers = {"content-type": "application/json"}
        resp.raise_for_status = MagicMock()
        resp.url = "https://consultas.anvisa.gov.br/api/consulta/medicamentos/arquivo/bula/parecer/ID001/"
        client.get.return_value = resp
        with pytest.raises(ValueError, match="Esperado PDF"):
            baixar_pdf("ID001", client=client)


# ---------------------------------------------------------------------------
# Fluxo de aquisição
# ---------------------------------------------------------------------------

class TestAdquirirMedicamento:
    def _mock_session(
        self,
        bula_existente=None,
        medicamento_existente=None,
    ):
        session = MagicMock()
        session.commit = MagicMock()
        return session

    def _mock_client(
        self,
        resultados_busca: list | None = None,
        conteudo_pdf: bytes = b"%PDF fake",
        status_busca: int = 200,
        status_pdf: int = 200,
    ):
        client = MagicMock()

        resp_busca = MagicMock()
        resp_busca.status_code = status_busca
        resp_busca.headers = {"content-type": "application/json"}
        resp_busca.url = "https://consultas.anvisa.gov.br/api/consulta/bulario"
        resp_busca.raise_for_status = MagicMock()
        if resultados_busca is not None:
            resp_busca.json.return_value = {"content": resultados_busca}
        else:
            resp_busca.json.return_value = {"content": [
                {
                    "nomeProduto": "DIPIRONA",
                    "idBulaProfissionalProtegido": "PROF001",
                    "idBulaPacienteProtegido": None,
                    "numExpediente": None,
                }
            ]}

        resp_pdf = MagicMock()
        resp_pdf.status_code = status_pdf
        resp_pdf.headers = {"content-type": "application/pdf"}
        resp_pdf.content = conteudo_pdf
        resp_pdf.raise_for_status = MagicMock()
        resp_pdf.url = "https://consultas.anvisa.gov.br/api/consulta/medicamentos/arquivo/bula/parecer/PROF001/"

        client.get.side_effect = [resp_busca, resp_pdf]
        return client

    def test_fluxo_completo_baixado(self, tmp_path):
        client = self._mock_client()

        with (
            patch("backend.aquisicao.fluxo.buscar_bulas") as mock_busca,
            patch("backend.aquisicao.fluxo.baixar_pdf") as mock_pdf,
            patch("backend.aquisicao.fluxo.buscar_bula_por_id_anvisa", return_value=None),
            patch("backend.aquisicao.fluxo.buscar_medicamento_por_nome", return_value=None),
            patch("backend.aquisicao.fluxo.criar_medicamento") as mock_criar_med,
            patch("backend.aquisicao.fluxo.criar_bula") as mock_criar_bula,
            patch("backend.aquisicao.fluxo.settings") as mock_settings,
        ):
            mock_busca.return_value = [
                ResultadoBusca(
                    id_bula_profissional="PROF001",
                    id_bula_paciente=None,
                    nome_produto="DIPIRONA",
                )
            ]
            mock_pdf.return_value = b"%PDF fake"
            mock_criar_med.return_value = MagicMock(id=1, bulas=[])
            mock_settings.bulas_dir = str(tmp_path)
            mock_settings.anvisa_tipo_bula = "paciente"
            mock_settings.anvisa_retry_tentativas = 3
            mock_settings.anvisa_retry_espera_segundos = 0.0

            session = MagicMock()
            log = _adquirir(session, "dipirona", client, reprocessar_erro=False)

        assert log.resultado == ResultadoAquisicao.BAIXADO
        assert log.id_bula == "PROF001"
        mock_criar_bula.assert_called_once()

    def test_skip_bula_existente(self, tmp_path):
        pdf_path = tmp_path / "dipirona__PROF001.pdf"
        pdf_path.write_bytes(b"%PDF fake")

        bula_mock = MagicMock()
        bula_mock.status_processamento_ia = StatusProcessamento.PENDENTE
        bula_mock.caminho_pdf = str(pdf_path)

        client = MagicMock()

        with (
            patch("backend.aquisicao.fluxo.buscar_bulas") as mock_busca,
            patch("backend.aquisicao.fluxo.buscar_bula_por_id_anvisa", return_value=bula_mock),
        ):
            mock_busca.return_value = [
                ResultadoBusca(
                    id_bula_profissional="PROF001",
                    id_bula_paciente=None,
                    nome_produto="DIPIRONA",
                )
            ]

            session = MagicMock()
            log = _adquirir(session, "dipirona", client, reprocessar_erro=False)

        assert log.resultado == ResultadoAquisicao.SKIP
        assert log.caminho_pdf == str(pdf_path)

    def test_nao_encontrado(self):
        client = MagicMock()

        with patch("backend.aquisicao.fluxo.buscar_bulas", return_value=[]):
            session = MagicMock()
            log = _adquirir(session, "medicamento_inexistente", client, reprocessar_erro=False)

        assert log.resultado == ResultadoAquisicao.NAO_ENCONTRADO

    def test_bloqueio_propaga(self):
        client = MagicMock()

        with patch("backend.aquisicao.fluxo.buscar_bulas", side_effect=BloqueioAnvisaError("403")):
            session = MagicMock()
            with pytest.raises(BloqueioAnvisaError):
                _adquirir(session, "dipirona", client, reprocessar_erro=False)

    def test_reprocessar_erro(self):
        bula_mock = MagicMock()
        bula_mock.id = 42
        bula_mock.status_processamento_ia = StatusProcessamento.ERRO
        bula_mock.caminho_pdf = "docs/bulas/dipirona__PROF001.pdf"

        client = MagicMock()

        with (
            patch("backend.aquisicao.fluxo.buscar_bulas") as mock_busca,
            patch("backend.aquisicao.fluxo.buscar_bula_por_id_anvisa", return_value=bula_mock),
            patch("backend.aquisicao.fluxo.atualizar_status_bula") as mock_atualizar,
        ):
            mock_busca.return_value = [
                ResultadoBusca(
                    id_bula_profissional="PROF001",
                    id_bula_paciente=None,
                    nome_produto="DIPIRONA",
                )
            ]

            session = MagicMock()
            log = _adquirir(session, "dipirona", client, reprocessar_erro=True)

        assert log.resultado == ResultadoAquisicao.REPROCESSADO
        mock_atualizar.assert_called_once_with(
            session, 42, StatusProcessamento.PENDENTE
        )

    def test_skip_erro_sem_reprocessar(self):
        bula_mock = MagicMock()
        bula_mock.id = 42
        bula_mock.status_processamento_ia = StatusProcessamento.ERRO
        bula_mock.caminho_pdf = "docs/bulas/dipirona__PROF001.pdf"

        client = MagicMock()

        with (
            patch("backend.aquisicao.fluxo.buscar_bulas") as mock_busca,
            patch("backend.aquisicao.fluxo.buscar_bula_por_id_anvisa", return_value=bula_mock),
        ):
            mock_busca.return_value = [
                ResultadoBusca(
                    id_bula_profissional="PROF001",
                    id_bula_paciente=None,
                    nome_produto="DIPIRONA",
                )
            ]

            session = MagicMock()
            log = _adquirir(session, "dipirona", client, reprocessar_erro=False)

        assert log.resultado == ResultadoAquisicao.SKIP


# ---------------------------------------------------------------------------
# Cenários de controle de duplicatas (A–D)
# ---------------------------------------------------------------------------

class TestCenariosSkip:
    """Testes para os 4 cenários de controle de duplicatas."""

    def _resultado_busca(self, id_bula="PROF001"):
        return [ResultadoBusca(id_bula_profissional=id_bula, id_bula_paciente=None, nome_produto="DIPIRONA")]

    def test_cenario_b_mesmo_jwt_arquivo_ausente_recuperado(self, tmp_path):
        bula_mock = MagicMock()
        bula_mock.id = 99
        bula_mock.status_processamento_ia = StatusProcessamento.PENDENTE
        bula_mock.caminho_pdf = str(tmp_path / "dipirona__PROF001.pdf")  # arquivo não existe

        with (
            patch("backend.aquisicao.fluxo.buscar_bulas") as mock_busca,
            patch("backend.aquisicao.fluxo.buscar_bula_por_id_anvisa", return_value=bula_mock),
            patch("backend.aquisicao.fluxo.baixar_pdf", return_value=b"%PDF fake"),
            patch("backend.aquisicao.fluxo.atualizar_status_bula") as mock_atualizar,
            patch("backend.aquisicao.fluxo.settings") as mock_settings,
        ):
            mock_busca.return_value = self._resultado_busca()
            mock_settings.bulas_dir = str(tmp_path)
            mock_settings.anvisa_tipo_bula = "paciente"
            mock_settings.anvisa_retry_tentativas = 3
            mock_settings.anvisa_retry_espera_segundos = 0.0

            session = MagicMock()
            log = _adquirir(session, "dipirona", MagicMock(), reprocessar_erro=False)

        assert log.resultado == ResultadoAquisicao.RECUPERADO
        assert log.id_bula == "PROF001"
        assert log.caminho_pdf is not None
        mock_atualizar.assert_called_once()
        assert mock_atualizar.call_args.kwargs.get("caminho_pdf") is not None

    def test_cenario_c_jwt_novo_arquivo_presente_skip(self, tmp_path):
        pdf_path = tmp_path / "dipirona__OLDID.pdf"
        pdf_path.write_bytes(b"%PDF fake old")

        bula_antiga = MagicMock()
        bula_antiga.id_bula_anvisa = "OLDIDXXXXXXXX"
        bula_antiga.caminho_pdf = str(pdf_path)

        med_mock = MagicMock()
        med_mock.bulas = [bula_antiga]

        with (
            patch("backend.aquisicao.fluxo.buscar_bulas") as mock_busca,
            patch("backend.aquisicao.fluxo.buscar_bula_por_id_anvisa", return_value=None),
            patch("backend.aquisicao.fluxo.buscar_medicamento_por_nome", return_value=med_mock),
            patch("backend.aquisicao.fluxo.baixar_pdf") as mock_baixar,
        ):
            mock_busca.return_value = self._resultado_busca(id_bula="NEWIDXXXXXXXX")

            session = MagicMock()
            log = _adquirir(session, "dipirona", MagicMock(), reprocessar_erro=False)

        assert log.resultado == ResultadoAquisicao.SKIP
        assert log.caminho_pdf == str(pdf_path)
        mock_baixar.assert_not_called()

    def test_cenario_d_jwt_novo_sem_arquivo_baixado_fantasmas_deletados(self, tmp_path):
        bula_fantasma = MagicMock()
        bula_fantasma.id_bula_anvisa = "OLDIDXXXXXXXX"
        bula_fantasma.caminho_pdf = str(tmp_path / "dipirona__OLDID.pdf")  # arquivo não existe

        med_mock = MagicMock()
        med_mock.id = 7
        med_mock.bulas = [bula_fantasma]
        med_mock.nome_dcb = "dipirona"

        with (
            patch("backend.aquisicao.fluxo.buscar_bulas") as mock_busca,
            patch("backend.aquisicao.fluxo.buscar_bula_por_id_anvisa", return_value=None),
            patch("backend.aquisicao.fluxo.buscar_medicamento_por_nome", return_value=med_mock),
            patch("backend.aquisicao.fluxo.baixar_pdf", return_value=b"%PDF fake"),
            patch("backend.aquisicao.fluxo.criar_bula") as mock_criar_bula,
            patch("backend.aquisicao.fluxo.settings") as mock_settings,
        ):
            mock_busca.return_value = self._resultado_busca(id_bula="NEWIDXXXXXXXX")
            mock_settings.bulas_dir = str(tmp_path)
            mock_settings.anvisa_tipo_bula = "paciente"
            mock_settings.anvisa_retry_tentativas = 3
            mock_settings.anvisa_retry_espera_segundos = 0.0

            session = MagicMock()
            log = _adquirir(session, "dipirona", MagicMock(), reprocessar_erro=False)

        assert log.resultado == ResultadoAquisicao.BAIXADO
        session.delete.assert_called_once_with(bula_fantasma)
        session.flush.assert_called()
        mock_criar_bula.assert_called_once()


# ---------------------------------------------------------------------------
# Fallback por nome comercial (2.16 / 2.17)
# ---------------------------------------------------------------------------

class TestBuscarFallbackNomeComercial:
    def _resultado(self, nome="ORENCIA"):
        return ResultadoBusca(
            id_bula_paciente="PAC001",
            id_bula_profissional="PROF001",
            nome_produto=nome,
        )

    def test_fallback_encontrado_via_nome_comercial(self):
        client = MagicMock()
        mapa = {"abatacepte": ["ORENCIA", "OUTRO"]}

        with patch("backend.aquisicao.fluxo._obter_mapa_referencia", return_value=mapa), \
             patch("backend.aquisicao.fluxo.buscar_bulas") as mock_busca, \
             patch("backend.aquisicao.fluxo.time") as mock_time:
            mock_busca.return_value = [self._resultado("ORENCIA")]
            mock_time.sleep = MagicMock()

            resultados, nome_usado = _buscar_fallback_nome_comercial("abatacepte", client)

        assert len(resultados) == 1
        assert nome_usado == "ORENCIA"
        mock_busca.assert_called_once_with("ORENCIA", client=client)

    def test_fallback_usa_primeiro_que_retorna_resultado(self):
        client = MagicMock()
        mapa = {"abatacepte": ["NOME_SEM_RESULTADO", "ORENCIA"]}

        with patch("backend.aquisicao.fluxo._obter_mapa_referencia", return_value=mapa), \
             patch("backend.aquisicao.fluxo.buscar_bulas") as mock_busca, \
             patch("backend.aquisicao.fluxo.time") as mock_time:
            mock_busca.side_effect = [[], [self._resultado("ORENCIA")]]
            mock_time.sleep = MagicMock()

            resultados, nome_usado = _buscar_fallback_nome_comercial("abatacepte", client)

        assert nome_usado == "ORENCIA"
        assert len(resultados) == 1

    def test_fallback_sem_correspondencia_nas_listas(self):
        client = MagicMock()
        mapa = {}  # DCB não está em nenhuma lista

        with patch("backend.aquisicao.fluxo._obter_mapa_referencia", return_value=mapa):
            resultados, nome_usado = _buscar_fallback_nome_comercial("farmaco_desconhecido", client)

        assert resultados == []
        assert nome_usado is None

    def test_fallback_todos_nomes_sem_resultado(self):
        client = MagicMock()
        mapa = {"abatacepte": ["NOME_A", "NOME_B"]}

        with patch("backend.aquisicao.fluxo._obter_mapa_referencia", return_value=mapa), \
             patch("backend.aquisicao.fluxo.buscar_bulas", return_value=[]), \
             patch("backend.aquisicao.fluxo.time") as mock_time:
            mock_time.sleep = MagicMock()

            resultados, nome_usado = _buscar_fallback_nome_comercial("abatacepte", client)

        assert resultados == []
        assert nome_usado is None

    def test_fallback_propaga_bloqueio(self):
        client = MagicMock()
        mapa = {"abatacepte": ["ORENCIA"]}

        with patch("backend.aquisicao.fluxo._obter_mapa_referencia", return_value=mapa), \
             patch("backend.aquisicao.fluxo.buscar_bulas", side_effect=BloqueioAnvisaError("429")):
            with pytest.raises(BloqueioAnvisaError):
                _buscar_fallback_nome_comercial("abatacepte", client)

    def test_adquirir_usa_nome_comercial_como_identificador(self, tmp_path):
        """Quando o fallback é ativado, o log usa o nome comercial e nome_dcb preserva o DCB."""
        mapa = {"abatacepte": ["ORENCIA"]}

        with (
            patch("backend.aquisicao.fluxo.buscar_bulas") as mock_busca,
            patch("backend.aquisicao.fluxo._obter_mapa_referencia", return_value=mapa),
            patch("backend.aquisicao.fluxo.baixar_pdf", return_value=b"%PDF fake"),
            patch("backend.aquisicao.fluxo.buscar_bula_por_id_anvisa", return_value=None),
            patch("backend.aquisicao.fluxo.buscar_medicamento_por_nome", return_value=None),
            patch("backend.aquisicao.fluxo.criar_medicamento") as mock_criar_med,
            patch("backend.aquisicao.fluxo.criar_bula"),
            patch("backend.aquisicao.fluxo.settings") as mock_settings,
            patch("backend.aquisicao.fluxo.time") as mock_time,
        ):
            mock_busca.side_effect = [
                [],
                [ResultadoBusca(id_bula_paciente="PAC001", id_bula_profissional=None, nome_produto="ORENCIA")],
            ]
            mock_criar_med.return_value = MagicMock(id=1, bulas=[])
            mock_settings.bulas_dir = str(tmp_path)
            mock_settings.anvisa_tipo_bula = "paciente"
            mock_settings.anvisa_delay_segundos = 0
            mock_settings.anvisa_retry_tentativas = 3
            mock_settings.anvisa_retry_espera_segundos = 0.0
            mock_time.sleep = MagicMock()

            session = MagicMock()
            log = _adquirir(session, "abatacepte", MagicMock(), reprocessar_erro=False)

        assert log.resultado == ResultadoAquisicao.BAIXADO
        assert log.nome == "ORENCIA"
        # nome_dcb deve ser o DCB original, nome_comercial o nome usado no fallback
        mock_criar_med.assert_called_once_with(
            session, nome_comercial="ORENCIA", nome_dcb="abatacepte"
        )

    def test_adquirir_sem_fallback_passa_nome_dcb_igual_comercial(self, tmp_path):
        """Quando o DCB é encontrado diretamente, nome_dcb e nome_comercial são iguais."""
        with (
            patch("backend.aquisicao.fluxo.buscar_bulas") as mock_busca,
            patch("backend.aquisicao.fluxo.baixar_pdf", return_value=b"%PDF fake"),
            patch("backend.aquisicao.fluxo.buscar_bula_por_id_anvisa", return_value=None),
            patch("backend.aquisicao.fluxo.buscar_medicamento_por_nome", return_value=None),
            patch("backend.aquisicao.fluxo.criar_medicamento") as mock_criar_med,
            patch("backend.aquisicao.fluxo.criar_bula"),
            patch("backend.aquisicao.fluxo.settings") as mock_settings,
        ):
            mock_busca.return_value = [
                ResultadoBusca(id_bula_paciente="PAC001", id_bula_profissional=None, nome_produto="DIPIRONA")
            ]
            mock_criar_med.return_value = MagicMock(id=1, bulas=[])
            mock_settings.bulas_dir = str(tmp_path)
            mock_settings.anvisa_tipo_bula = "paciente"
            mock_settings.anvisa_retry_tentativas = 3
            mock_settings.anvisa_retry_espera_segundos = 0.0

            session = MagicMock()
            _adquirir(session, "dipirona", MagicMock(), reprocessar_erro=False)

        mock_criar_med.assert_called_once_with(
            session, nome_comercial="dipirona", nome_dcb="dipirona"
        )

    def test_adquirir_preenche_nome_dcb_retroativamente(self, tmp_path):
        """Medicamento já existente sem nome_dcb deve ter o campo preenchido."""
        med_existente = MagicMock()
        med_existente.id = 5
        med_existente.bulas = []
        med_existente.nome_dcb = None  # sem nome_dcb ainda

        with (
            patch("backend.aquisicao.fluxo.buscar_bulas") as mock_busca,
            patch("backend.aquisicao.fluxo.baixar_pdf", return_value=b"%PDF fake"),
            patch("backend.aquisicao.fluxo.buscar_bula_por_id_anvisa", return_value=None),
            patch("backend.aquisicao.fluxo.buscar_medicamento_por_nome", return_value=med_existente),
            patch("backend.aquisicao.fluxo.criar_bula"),
            patch("backend.aquisicao.fluxo.settings") as mock_settings,
        ):
            mock_busca.return_value = [
                ResultadoBusca(id_bula_paciente="PAC001", id_bula_profissional=None, nome_produto="DIPIRONA")
            ]
            mock_settings.bulas_dir = str(tmp_path)
            mock_settings.anvisa_tipo_bula = "paciente"
            mock_settings.anvisa_retry_tentativas = 3
            mock_settings.anvisa_retry_espera_segundos = 0.0

            session = MagicMock()
            _adquirir(session, "dipirona", MagicMock(), reprocessar_erro=False)

        assert med_existente.nome_dcb == "dipirona"


# ---------------------------------------------------------------------------
# ErroTransitorioAnvisaError (4.1)
# ---------------------------------------------------------------------------

class TestErroTransitorio:
    def _resp(self, status_code: int, content_type: str = "application/json"):
        resp = MagicMock()
        resp.status_code = status_code
        resp.headers = {"content-type": content_type}
        resp.url = "https://consultas.anvisa.gov.br/api/consulta/bulario"
        resp.text = ""
        return resp

    def test_status_500_levanta_erro_transitorio(self):
        from backend.aquisicao.cliente import _verificar_bloqueio
        with pytest.raises(ErroTransitorioAnvisaError):
            _verificar_bloqueio(self._resp(500))

    def test_status_503_levanta_erro_transitorio(self):
        from backend.aquisicao.cliente import _verificar_bloqueio
        with pytest.raises(ErroTransitorioAnvisaError):
            _verificar_bloqueio(self._resp(503))

    def test_status_200_nao_levanta(self):
        from backend.aquisicao.cliente import _verificar_bloqueio
        _verificar_bloqueio(self._resp(200))  # não deve lançar

    def test_status_404_nao_levanta_erro_transitorio(self):
        from backend.aquisicao.cliente import _verificar_bloqueio
        # 404 não é 5xx — não levanta ErroTransitorioAnvisaError
        # (raise_for_status() trata depois)
        _verificar_bloqueio(self._resp(404))


# ---------------------------------------------------------------------------
# _com_retry (4.2)
# ---------------------------------------------------------------------------

class TestComRetry:
    def test_sucesso_na_primeira_tentativa(self):
        fn = MagicMock(return_value="ok")
        with patch("backend.aquisicao.fluxo.settings") as mock_cfg, \
             patch("backend.aquisicao.fluxo.time") as mock_time:
            mock_cfg.anvisa_retry_tentativas = 3
            mock_cfg.anvisa_retry_espera_segundos = 1.0
            mock_time.sleep = MagicMock()
            resultado = _com_retry(fn, "arg1", kw="val")
        assert resultado == "ok"
        fn.assert_called_once_with("arg1", kw="val")
        mock_time.sleep.assert_not_called()

    def test_sucesso_na_segunda_tentativa(self):
        fn = MagicMock(side_effect=[ErroTransitorioAnvisaError("500"), "ok"])
        with patch("backend.aquisicao.fluxo.settings") as mock_cfg, \
             patch("backend.aquisicao.fluxo.time") as mock_time:
            mock_cfg.anvisa_retry_tentativas = 3
            mock_cfg.anvisa_retry_espera_segundos = 1.0
            mock_time.sleep = MagicMock()
            resultado = _com_retry(fn)
        assert resultado == "ok"
        assert fn.call_count == 2
        mock_time.sleep.assert_called_once_with(1.0)

    def test_esgotamento_de_tentativas_propaga_erro(self):
        fn = MagicMock(side_effect=ErroTransitorioAnvisaError("500"))
        with patch("backend.aquisicao.fluxo.settings") as mock_cfg, \
             patch("backend.aquisicao.fluxo.time") as mock_time:
            mock_cfg.anvisa_retry_tentativas = 3
            mock_cfg.anvisa_retry_espera_segundos = 1.0
            mock_time.sleep = MagicMock()
            with pytest.raises(ErroTransitorioAnvisaError):
                _com_retry(fn)
        assert fn.call_count == 3

    def test_erro_permanente_nao_dispara_retry(self):
        fn = MagicMock(side_effect=AcessoNegadoError("403"))
        with patch("backend.aquisicao.fluxo.settings") as mock_cfg, \
             patch("backend.aquisicao.fluxo.time") as mock_time:
            mock_cfg.anvisa_retry_tentativas = 3
            mock_cfg.anvisa_retry_espera_segundos = 1.0
            mock_time.sleep = MagicMock()
            with pytest.raises(AcessoNegadoError):
                _com_retry(fn)
        fn.assert_called_once()
        mock_time.sleep.assert_not_called()

    def test_backoff_exponencial(self):
        fn = MagicMock(side_effect=[
            ErroTransitorioAnvisaError("500"),
            ErroTransitorioAnvisaError("500"),
            "ok",
        ])
        sleeps = []
        with patch("backend.aquisicao.fluxo.settings") as mock_cfg, \
             patch("backend.aquisicao.fluxo.time") as mock_time:
            mock_cfg.anvisa_retry_tentativas = 3
            mock_cfg.anvisa_retry_espera_segundos = 2.0
            mock_time.sleep = MagicMock(side_effect=lambda s: sleeps.append(s))
            _com_retry(fn)
        assert sleeps == [2.0, 4.0]

    def test_adquirir_usa_retry_em_busca_e_retorna_baixado(self, tmp_path):
        """Integração: 500 na busca → retry → sucesso."""
        with (
            patch("backend.aquisicao.fluxo.buscar_bulas") as mock_busca,
            patch("backend.aquisicao.fluxo.baixar_pdf", return_value=b"%PDF fake"),
            patch("backend.aquisicao.fluxo.buscar_bula_por_id_anvisa", return_value=None),
            patch("backend.aquisicao.fluxo.buscar_medicamento_por_nome", return_value=None),
            patch("backend.aquisicao.fluxo.criar_medicamento") as mock_criar_med,
            patch("backend.aquisicao.fluxo.criar_bula"),
            patch("backend.aquisicao.fluxo.settings") as mock_settings,
            patch("backend.aquisicao.fluxo.time") as mock_time,
        ):
            mock_busca.side_effect = [
                ErroTransitorioAnvisaError("500"),
                [ResultadoBusca(id_bula_paciente="PAC001", id_bula_profissional=None, nome_produto="DIPIRONA")],
            ]
            mock_criar_med.return_value = MagicMock(id=1, bulas=[])
            mock_settings.bulas_dir = str(tmp_path)
            mock_settings.anvisa_tipo_bula = "paciente"
            mock_settings.anvisa_retry_tentativas = 3
            mock_settings.anvisa_retry_espera_segundos = 0.0
            mock_time.sleep = MagicMock()

            session = MagicMock()
            log = _adquirir(session, "dipirona", MagicMock(), reprocessar_erro=False)

        assert log.resultado == ResultadoAquisicao.BAIXADO


# ---------------------------------------------------------------------------
# Loader RENAME (smoke test sem rede)
# ---------------------------------------------------------------------------

class TestCarregarNomesRename:
    def test_retorna_lista_nao_vazia(self):
        nomes = carregar_nomes_rename()
        assert len(nomes) > 0

    def test_nomes_normalizados(self):
        nomes = carregar_nomes_rename()
        for nome in nomes[:20]:
            assert nome == nome.lower(), f"Nome nao esta em minusculas: {nome}"
            assert "  " not in nome, f"Espacos duplicados em: {nome}"
