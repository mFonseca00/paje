"""Testes unitários para o módulo de pré-processamento (formato bula paciente).

Usa fixtures de markdown sintético que espelham a estrutura real das bulas da
ANVISA: seções numeradas com nível de heading variável (# a ######), negrito
nos títulos e subseções não-numeradas dentro das seções principais.
"""
import pytest

from backend.preprocessamento.extrator import ResultadoPreprocessamento, extrair_secoes_relevantes

# ---------------------------------------------------------------------------
# Fixtures de markdown — formato bula paciente
# ---------------------------------------------------------------------------

# Estrutura completa: seções 1-9, nível ######, com subseção não-numerada em 4
MARKDOWN_BULA_PACIENTE_COMPLETA = """\
###### **I) IDENTIFICAÇÃO DO MEDICAMENTO**

Algum medicamento genérico.

###### **1. PARA QUE ESTE MEDICAMENTO É INDICADO?**

Indicado para tratamento de infecções bacterianas.

###### **2. COMO ESTE MEDICAMENTO FUNCIONA?**

Age inibindo a síntese da parede celular bacteriana.

###### **3. QUANDO NÃO DEVO USAR ESTE MEDICAMENTO?**

Este medicamento é contraindicado em casos de hipersensibilidade ao princípio ativo.
Não usar em menores de 3 meses de idade.

###### **4. O QUE DEVO SABER ANTES DE USAR ESTE MEDICAMENTO?**

Idosos e pacientes com insuficiência renal devem usar com cautela.

###### **Interações medicamentosas**

Pode interagir com anticoagulantes orais, reduzindo seu efeito.
Evitar uso concomitante com metotrexato.

###### **5. ONDE, COMO E POR QUANTO TEMPO POSSO GUARDAR ESTE MEDICAMENTO?**

Conservar em temperatura ambiente (entre 15°C e 30°C).

###### **8. QUAIS OS MALES QUE ESTE MEDICAMENTO PODE ME CAUSAR?**

Náusea e diarreia podem ocorrer.
"""

# Apenas seção 3, sem seção 4 — nível #
MARKDOWN_APENAS_SECAO_3 = """\
# **1. PARA QUE ESTE MEDICAMENTO É INDICADO?**

Indicado para X.

# **3. QUANDO NÃO DEVO USAR ESTE MEDICAMENTO?**

Contraindicado em casos de hipersensibilidade.
Não usar durante gravidez.

# **5. ONDE, COMO E POR QUANTO TEMPO POSSO GUARDAR ESTE MEDICAMENTO?**

Temperatura ambiente.
"""

# Apenas seção 4, sem seção 3 — nível ###
MARKDOWN_APENAS_SECAO_4 = """\
### **2. COMO ESTE MEDICAMENTO FUNCIONA?**

Age de tal forma.

### **4. O QUE DEVO SABER ANTES DE USAR ESTE MEDICAMENTO?**

Advertências importantes. Interações medicamentosas relevantes.

### **5. ONDE, COMO E POR QUANTO TEMPO POSSO GUARDAR ESTE MEDICAMENTO?**

Temperatura ambiente.
"""

# Seções 3 e 4 com nível ## (diferente do padrão ######)
MARKDOWN_NIVEL_HEADING_VARIAVEL = """\
## **1. PARA QUE ESTE MEDICAMENTO É INDICADO?**

Indicado para Y.

## **3. QUANDO NÃO DEVO USAR ESTE MEDICAMENTO?**

Contraindicado em insuficiência hepática grave.

## **4. O QUE DEVO SABER ANTES DE USAR ESTE MEDICAMENTO?**

Precauções especiais para idosos.

## **5. ONDE, COMO E POR QUANTO TEMPO POSSO GUARDAR ESTE MEDICAMENTO?**

Conservar ao abrigo da luz.
"""

# Sem seções 3 ou 4
MARKDOWN_SEM_SECOES_ALVO = """\
# **1. PARA QUE ESTE MEDICAMENTO É INDICADO?**

Indicado para Z.

# **2. COMO ESTE MEDICAMENTO FUNCIONA?**

Age desta forma.

# **5. ONDE, COMO E POR QUANTO TEMPO POSSO GUARDAR ESTE MEDICAMENTO?**

Temperatura ambiente.
"""

MARKDOWN_SEM_HEADINGS = "Texto simples sem nenhuma seção ou heading."

# Seção com <sup> no título (caso real DEPAKENE)
MARKDOWN_COM_SUPERSCRIPT = """\
##### **3. QUANDO NÃO DEVO USAR ESTE MEDICAMENTO? DEPAKENE**<sup>**®**</sup> **é contraindicado para:**

Pacientes com insuficiência hepática.

##### **5. ONDE, COMO E POR QUANTO TEMPO POSSO GUARDAR ESTE MEDICAMENTO?**

Temperatura ambiente.
"""

# Seções 5 e 6 em formato bold puro sem # (caso real acetato de hidrocortisona)
MARKDOWN_SECOES_BOLD_PURO = """\
### **3. QUANDO NÃO DEVO USAR ESTE MEDICAMENTO?**

Contraindicado em hipersensibilidade.

### **4. O QUE DEVO SABER ANTES DE USAR ESTE MEDICAMENTO?**

Advertências gerais.

**Interações com medicamentos, alimentos e exames laboratoriais**

Pode interagir com cimetidina e praziquantel.

**5. ONDE, COMO E POR QUANTO TEMPO POSSO GUARDAR ESTE MEDICAMENTO?** ARMAZENAR EM TEMPERATURA AMBIENTE.

**6. COMO DEVO USAR ESTE MEDICAMENTO? Como aplicar:**

Aplicar conforme orientação médica.
"""

# Bold que são parágrafos (devem permanecer como texto, não virar ###)
MARKDOWN_BOLD_PARAGRAFOS = """\
### **3. QUANDO NÃO DEVO USAR ESTE MEDICAMENTO?**

**Este medicamento não deve ser utilizado por mulheres grávidas sem orientação médica.**

### **4. O QUE DEVO SABER ANTES DE USAR ESTE MEDICAMENTO?**

**Informe ao seu médico se está fazendo uso de algum outro medicamento.**

**Interações medicamentosas**

Pode interagir com anticoagulantes.

### **5. ONDE, COMO E POR QUANTO TEMPO POSSO GUARDAR ESTE MEDICAMENTO?**

Temperatura ambiente.
"""


# ---------------------------------------------------------------------------
# Testes: extração das seções-alvo
# ---------------------------------------------------------------------------

class TestExtracaoSecoesAlvo:
    def test_extrai_secoes_3_e_4(self):
        resultado = extrair_secoes_relevantes(MARKDOWN_BULA_PACIENTE_COMPLETA)

        assert not resultado.markdown_bruto_usado
        assert len(resultado.secoes_encontradas) == 2

    def test_conteudo_secao_3_presente(self):
        resultado = extrair_secoes_relevantes(MARKDOWN_BULA_PACIENTE_COMPLETA)

        assert "menores de 3 meses" in resultado.texto
        assert "hipersensibilidade ao princípio ativo" in resultado.texto

    def test_conteudo_secao_4_presente(self):
        resultado = extrair_secoes_relevantes(MARKDOWN_BULA_PACIENTE_COMPLETA)

        assert "insuficiência renal" in resultado.texto
        assert "anticoagulantes orais" in resultado.texto

    def test_subsecao_nao_numerada_capturada(self):
        resultado = extrair_secoes_relevantes(MARKDOWN_BULA_PACIENTE_COMPLETA)

        assert "Interações medicamentosas" in resultado.texto

    def test_secoes_fora_do_alvo_ausentes(self):
        resultado = extrair_secoes_relevantes(MARKDOWN_BULA_PACIENTE_COMPLETA)

        assert "IDENTIFICAÇÃO" not in resultado.texto
        assert "PARA QUE ESTE MEDICAMENTO É INDICADO" not in resultado.texto
        assert "QUAIS OS MALES" not in resultado.texto
        assert "GUARDAR" not in resultado.texto

    def test_extrai_apenas_secao_3(self):
        resultado = extrair_secoes_relevantes(MARKDOWN_APENAS_SECAO_3)

        assert not resultado.markdown_bruto_usado
        assert len(resultado.secoes_encontradas) == 1
        assert "Contraindicado" in resultado.texto
        assert "GUARDAR" not in resultado.texto

    def test_extrai_apenas_secao_4(self):
        resultado = extrair_secoes_relevantes(MARKDOWN_APENAS_SECAO_4)

        assert not resultado.markdown_bruto_usado
        assert len(resultado.secoes_encontradas) == 1
        assert "Advertências" in resultado.texto
        assert "GUARDAR" not in resultado.texto

    def test_funciona_com_nivel_heading_variavel(self):
        resultado = extrair_secoes_relevantes(MARKDOWN_NIVEL_HEADING_VARIAVEL)

        assert not resultado.markdown_bruto_usado
        assert len(resultado.secoes_encontradas) == 2
        assert "insuficiência hepática" in resultado.texto
        assert "Precauções especiais" in resultado.texto

    def test_remove_superscript_do_nome_secao(self):
        resultado = extrair_secoes_relevantes(MARKDOWN_COM_SUPERSCRIPT)

        assert not resultado.markdown_bruto_usado
        assert "<sup>" not in resultado.secoes_encontradas[0]
        assert "®" not in resultado.secoes_encontradas[0]


# ---------------------------------------------------------------------------
# Testes: normalização de headings (tarefa 3.7)
# ---------------------------------------------------------------------------

class TestNormalizacaoHeadings:
    def test_secao_numerada_vira_h2(self):
        resultado = extrair_secoes_relevantes(MARKDOWN_BULA_PACIENTE_COMPLETA)

        linhas = resultado.texto.splitlines()
        headings = [l for l in linhas if l.startswith("#")]
        headings_numerados = [l for l in headings if l[3:4].isdigit()]

        assert all(l.startswith("## ") for l in headings_numerados)

    def test_subsecao_nao_numerada_vira_h3(self):
        resultado = extrair_secoes_relevantes(MARKDOWN_BULA_PACIENTE_COMPLETA)

        linhas = resultado.texto.splitlines()
        headings = [l for l in linhas if l.startswith("#")]
        headings_nao_numerados = [l for l in headings if not l[3:4].isdigit()]

        assert all(l.startswith("### ") for l in headings_nao_numerados)

    def test_heading_nao_contem_negrito(self):
        resultado = extrair_secoes_relevantes(MARKDOWN_BULA_PACIENTE_COMPLETA)

        linhas = resultado.texto.splitlines()
        headings = [l for l in linhas if l.startswith("#")]

        assert not any("**" in l for l in headings)

    def test_heading_nao_contem_mark(self):
        resultado = extrair_secoes_relevantes(MARKDOWN_BULA_PACIENTE_COMPLETA)

        assert "<mark>" not in resultado.texto
        assert "</mark>" not in resultado.texto

    def test_nivel_original_ignorado(self):
        # Mesmo com ## no original, deve normalizar para ##/### consistente
        resultado = extrair_secoes_relevantes(MARKDOWN_NIVEL_HEADING_VARIAVEL)

        linhas = resultado.texto.splitlines()
        headings = [l for l in linhas if l.startswith("#")]

        assert all(l.startswith("## ") or l.startswith("### ") for l in headings)


# ---------------------------------------------------------------------------
# Testes: nomes das seções encontradas
# ---------------------------------------------------------------------------

class TestNomesSecoesEncontradas:
    def test_nomes_sem_negrito(self):
        resultado = extrair_secoes_relevantes(MARKDOWN_BULA_PACIENTE_COMPLETA)

        assert not any("**" in nome for nome in resultado.secoes_encontradas)

    def test_nomes_contem_texto_da_secao(self):
        resultado = extrair_secoes_relevantes(MARKDOWN_BULA_PACIENTE_COMPLETA)

        nomes = resultado.secoes_encontradas
        assert any("3." in nome for nome in nomes)
        assert any("4." in nome for nome in nomes)


# ---------------------------------------------------------------------------
# Testes: fallback para markdown bruto
# ---------------------------------------------------------------------------

class TestMarkdownBruto:
    def test_retorna_bruto_quando_sem_secoes_alvo(self):
        resultado = extrair_secoes_relevantes(MARKDOWN_SEM_SECOES_ALVO)

        assert resultado.markdown_bruto_usado
        assert resultado.secoes_encontradas == []
        assert resultado.texto == MARKDOWN_SEM_SECOES_ALVO

    def test_retorna_bruto_quando_sem_headings(self):
        resultado = extrair_secoes_relevantes(MARKDOWN_SEM_HEADINGS)

        assert resultado.markdown_bruto_usado
        assert resultado.texto == MARKDOWN_SEM_HEADINGS

    def test_texto_integro_no_modo_bruto(self):
        resultado = extrair_secoes_relevantes(MARKDOWN_SEM_SECOES_ALVO)

        assert "PARA QUE ESTE MEDICAMENTO É INDICADO" in resultado.texto
        assert "GUARDAR" in resultado.texto


# ---------------------------------------------------------------------------
# Testes: seções em formato bold puro (sem #) — bug acetato de hidrocortisona
# ---------------------------------------------------------------------------

class TestSecoesBoldPuro:
    def test_secao_bold_puro_usada_como_fronteira(self):
        # Seções 5 e 6 em bold puro (sem #) não devem aparecer no output
        resultado = extrair_secoes_relevantes(MARKDOWN_SECOES_BOLD_PURO)

        assert not resultado.markdown_bruto_usado
        assert "GUARDAR" not in resultado.texto
        assert "COMO DEVO USAR" not in resultado.texto

    def test_conteudo_secoes_3_e_4_presente(self):
        resultado = extrair_secoes_relevantes(MARKDOWN_SECOES_BOLD_PURO)

        assert "Contraindicado em hipersensibilidade" in resultado.texto
        assert "Advertências gerais" in resultado.texto

    def test_bold_subheading_vira_h3(self):
        # "Interações com medicamentos..." é bold puro sem ponto → deve virar ###
        resultado = extrair_secoes_relevantes(MARKDOWN_SECOES_BOLD_PURO)

        assert "### Interações com medicamentos, alimentos e exames laboratoriais" in resultado.texto

    def test_bold_paragrafo_permanece_como_texto(self):
        # Linhas bold que terminam com ponto não devem virar heading
        resultado = extrair_secoes_relevantes(MARKDOWN_BOLD_PARAGRAFOS)

        linhas = resultado.texto.splitlines()
        # Nenhum heading deve conter "grávidas" ou "Informe"
        headings = [l for l in linhas if l.startswith("#")]
        assert not any("grávidas" in h or "Informe" in h for h in headings)

    def test_bold_subheading_sem_pontuacao_vira_h3(self):
        resultado = extrair_secoes_relevantes(MARKDOWN_BOLD_PARAGRAFOS)

        assert "### Interações medicamentosas" in resultado.texto

    def test_secoes_alvo_encontradas_com_fronteira_bold(self):
        resultado = extrair_secoes_relevantes(MARKDOWN_SECOES_BOLD_PURO)

        assert len(resultado.secoes_encontradas) == 2
        assert any("3." in nome for nome in resultado.secoes_encontradas)
        assert any("4." in nome for nome in resultado.secoes_encontradas)
