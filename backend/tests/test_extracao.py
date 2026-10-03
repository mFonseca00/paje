"""Testes unitários do módulo de extração com mock do agente LLM."""
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from backend.extracao.agente import _buscar_secao, _carregar_prompt
from backend.extracao.schemas import ContraIndicacao, ExtracacaoClinica, InteracaoMedicamentosa


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def extracao_simples() -> ExtracacaoClinica:
    return ExtracacaoClinica(
        contraindicacoes=[
            ContraIndicacao(ordinal=1, descricao="Alergia a penicilinas"),
            ContraIndicacao(ordinal=2, descricao="Mononucleose infecciosa"),
        ],
        interacoes=[
            InteracaoMedicamentosa(ordinal=1, tipo="NOME_DIRETO", referencia="probenecida",
                                   efeito="retarda excreção renal"),
            InteracaoMedicamentosa(ordinal=2, tipo="CLASSE", referencia="anticoagulantes cumarínicos",
                                   efeito="prolonga tempo de protrombina"),
            InteracaoMedicamentosa(ordinal=3, tipo="ALIMENTO", referencia="bebidas alcoólicas",
                                   efeito=None),
        ],
    )


@pytest.fixture
def markdown_bruto_exemplo() -> str:
    return """# Dipirona Sódica — Bula Completa

## 1. Identificação do medicamento

Dipirona sódica 500mg comprimido.

## 2. Composição

Cada comprimido contém dipirona sódica 500mg.

## 3. Quando não devo usar este medicamento?

Não use se tiver alergia à dipirona ou derivados pirazolônicos.
Não use em casos de asma brônquica grave.

## 4. O que devo saber antes de usar este medicamento?

### Interações medicamentosas

O uso concomitante com anticoagulantes cumarínicos pode aumentar o efeito anticoagulante.

Ver item 4.5 para informações adicionais sobre interações.

## 4.5 Interações específicas com outros medicamentos

O metotrexato tem sua toxicidade aumentada quando usado com dipirona.
Ciclosporina tem seus níveis reduzidos.

## 5. Como devo usar este medicamento?

Adultos: 1 comprimido 4 vezes ao dia.
"""


@pytest.fixture
def arquivo_secoes_tmp(tmp_path) -> Path:
    conteudo = """## 3. Quando não devo usar este medicamento?

Não use se tiver alergia à dipirona ou derivados pirazolônicos.
Não use em casos de asma brônquica grave.

## 4. O que devo saber antes de usar este medicamento?

### Interações medicamentosas

O uso concomitante com anticoagulantes cumarínicos pode aumentar o efeito anticoagulante.
"""
    arquivo = tmp_path / "bula__secoes.md"
    arquivo.write_text(conteudo, encoding="utf-8")
    return arquivo


@pytest.fixture
def arquivo_bruto_tmp(tmp_path, markdown_bruto_exemplo) -> Path:
    arquivo = tmp_path / "bula__bruto.md"
    arquivo.write_text(markdown_bruto_exemplo, encoding="utf-8")
    return arquivo


# ---------------------------------------------------------------------------
# Testes: schemas Pydantic
# ---------------------------------------------------------------------------

class TestSchemas:
    def test_contraindicacao_valida(self):
        ci = ContraIndicacao(ordinal=1, descricao="Alergia a penicilinas")
        assert ci.ordinal == 1
        assert ci.descricao == "Alergia a penicilinas"

    def test_interacao_nome_direto(self):
        i = InteracaoMedicamentosa(ordinal=1, tipo="NOME_DIRETO", referencia="varfarina",
                                   efeito="aumenta risco de sangramento")
        assert i.tipo == "NOME_DIRETO"
        assert i.efeito == "aumenta risco de sangramento"

    def test_interacao_efeito_nullable(self):
        i = InteracaoMedicamentosa(ordinal=1, tipo="ALIMENTO", referencia="leite", efeito=None)
        assert i.efeito is None

    def test_interacao_tipo_invalido(self):
        with pytest.raises(Exception):
            InteracaoMedicamentosa(ordinal=1, tipo="INVALIDO", referencia="x")

    def test_extracao_clinica_completa(self, extracao_simples):
        assert len(extracao_simples.contraindicacoes) == 2
        assert len(extracao_simples.interacoes) == 3

    def test_extracao_serializa_json(self, extracao_simples):
        dados = extracao_simples.model_dump()
        assert "contraindicacoes" in dados
        assert "interacoes" in dados
        assert dados["interacoes"][0]["tipo"] == "NOME_DIRETO"
        assert dados["interacoes"][2]["efeito"] is None

    def test_extracao_listas_vazias(self):
        e = ExtracacaoClinica(contraindicacoes=[], interacoes=[])
        assert e.contraindicacoes == []
        assert e.interacoes == []


# ---------------------------------------------------------------------------
# Testes: _buscar_secao
# ---------------------------------------------------------------------------

class TestBuscarSecao:
    def test_busca_por_numero_simples(self, markdown_bruto_exemplo):
        resultado = _buscar_secao(markdown_bruto_exemplo, "4.5")
        assert resultado is not None
        assert "metotrexato" in resultado.lower()

    def test_busca_por_numero_com_texto(self, markdown_bruto_exemplo):
        resultado = _buscar_secao(markdown_bruto_exemplo, "seção 4.5")
        assert resultado is not None
        assert "metotrexato" in resultado.lower()

    def test_busca_por_item(self, markdown_bruto_exemplo):
        resultado = _buscar_secao(markdown_bruto_exemplo, "item 4.5")
        assert resultado is not None

    def test_secao_nao_encontrada(self, markdown_bruto_exemplo):
        resultado = _buscar_secao(markdown_bruto_exemplo, "99.9")
        assert resultado is None

    def test_secao_inicial(self, markdown_bruto_exemplo):
        resultado = _buscar_secao(markdown_bruto_exemplo, "2")
        assert resultado is not None
        assert "composição" in resultado.lower() or "comprimido" in resultado.lower()


# ---------------------------------------------------------------------------
# Testes: extrair_bula com mock do agente
# ---------------------------------------------------------------------------

class TestExtrairBula:
    def test_extrai_com_mock(self, arquivo_secoes_tmp, arquivo_bruto_tmp, extracao_simples):
        mock_resultado = MagicMock()
        mock_resultado.output = extracao_simples
        mock_agente = MagicMock()
        mock_agente.run_sync.return_value = mock_resultado

        with patch("backend.extracao.agente._get_agente", return_value=mock_agente):
            from backend.extracao.agente import extrair_bula
            resultado = extrair_bula(arquivo_secoes_tmp, arquivo_bruto_tmp)

        assert resultado is extracao_simples
        mock_agente.run_sync.assert_called_once()

    def test_texto_secoes_passado_ao_agente(self, arquivo_secoes_tmp, arquivo_bruto_tmp,
                                             extracao_simples):
        conteudo_esperado = arquivo_secoes_tmp.read_text(encoding="utf-8")
        mock_resultado = MagicMock()
        mock_resultado.output = extracao_simples
        mock_agente = MagicMock()
        mock_agente.run_sync.return_value = mock_resultado

        with patch("backend.extracao.agente._get_agente", return_value=mock_agente):
            from backend.extracao.agente import extrair_bula
            extrair_bula(arquivo_secoes_tmp, arquivo_bruto_tmp)

        args, _ = mock_agente.run_sync.call_args
        assert args[0] == conteudo_esperado

    def test_caminho_bruto_passado_como_deps(self, arquivo_secoes_tmp, arquivo_bruto_tmp,
                                              extracao_simples):
        mock_resultado = MagicMock()
        mock_resultado.output = extracao_simples
        mock_agente = MagicMock()
        mock_agente.run_sync.return_value = mock_resultado

        with patch("backend.extracao.agente._get_agente", return_value=mock_agente):
            from backend.extracao.agente import extrair_bula, ContextoBula
            extrair_bula(arquivo_secoes_tmp, arquivo_bruto_tmp)

        _, kwargs = mock_agente.run_sync.call_args
        assert isinstance(kwargs["deps"], ContextoBula)
        assert kwargs["deps"].caminho_bruto == arquivo_bruto_tmp

    def test_propaga_excecao_do_agente(self, arquivo_secoes_tmp, arquivo_bruto_tmp):
        mock_agente = MagicMock()
        mock_agente.run_sync.side_effect = RuntimeError("Timeout do modelo")

        with patch("backend.extracao.agente._get_agente", return_value=mock_agente):
            from backend.extracao.agente import extrair_bula
            with pytest.raises(RuntimeError, match="Timeout do modelo"):
                extrair_bula(arquivo_secoes_tmp, arquivo_bruto_tmp)


# ---------------------------------------------------------------------------
# Testes: pipeline — processar_bula com mock
# ---------------------------------------------------------------------------

class TestPipeline:
    def test_processa_bula_sem_pdf(self):
        from backend.extracao.pipeline import processar_bula, ResultadoExtracao
        from backend.armazenamento.modelos import Bula, StatusProcessamento

        bula = Bula()
        bula.id = 1
        bula.id_bula_anvisa = "abc123"
        bula.caminho_pdf = None
        bula.status_processamento_ia = StatusProcessamento.PENDENTE

        with patch("backend.extracao.pipeline._garantir_markdown", return_value=None):
            log = processar_bula(bula)

        assert log.resultado == ResultadoExtracao.SEM_PDF

    def test_processa_bula_com_sucesso(self, arquivo_secoes_tmp, arquivo_bruto_tmp,
                                        extracao_simples):
        from backend.extracao.pipeline import processar_bula, ResultadoExtracao
        from backend.armazenamento.modelos import Bula, StatusProcessamento

        bula = Bula()
        bula.id = 99
        bula.id_bula_anvisa = "xyz999"
        bula.caminho_pdf = "docs/bulas/fake.pdf"
        bula.status_processamento_ia = StatusProcessamento.PENDENTE

        with (
            patch("backend.extracao.pipeline._garantir_markdown",
                  return_value=(arquivo_secoes_tmp, arquivo_bruto_tmp)),
            patch("backend.extracao.pipeline.extrair_bula", return_value=extracao_simples),
            patch("backend.extracao.pipeline.atualizar_status_bula"),
            patch("backend.extracao.pipeline.criar_contraindicacao"),
            patch("backend.extracao.pipeline.criar_interacao"),
            patch("backend.extracao.pipeline.SessionLocal") as mock_session,
        ):
            mock_session.return_value.__enter__ = MagicMock(return_value=MagicMock())
            mock_session.return_value.__exit__ = MagicMock(return_value=False)
            log = processar_bula(bula)

        assert log.resultado == ResultadoExtracao.PROCESSADO
        assert log.contraindicacoes == 2
        assert log.interacoes == 3
