from datetime import datetime

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from backend.armazenamento.modelos import (
    Base,
    Bula,
    Contraindicacao,
    InteracaoMedicamentosa,
    Medicamento,
    StatusProcessamento,
    SubstanciaMedicamento,
)
from backend.config import settings

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine)


def get_session() -> Session:
    return SessionLocal()


# --- Medicamentos ---

def criar_medicamento(
    session: Session,
    nome_comercial: str,
    substancia_ativa: str | None = None,
    nome_dcb: str | None = None,
) -> Medicamento:
    med = Medicamento(nome_comercial=nome_comercial, substancia_ativa=substancia_ativa, nome_dcb=nome_dcb)
    session.add(med)
    session.flush()
    return med


def buscar_medicamento_por_nome(session: Session, nome: str) -> Medicamento | None:
    """Busca por nome_comercial ou nome_dcb para evitar duplicatas."""
    return session.scalars(
        select(Medicamento).where(
            (Medicamento.nome_comercial == nome) | (Medicamento.nome_dcb == nome)
        )
    ).first()


def listar_medicamentos(session: Session) -> list[Medicamento]:
    return list(session.scalars(select(Medicamento)).all())


# --- Bulas ---

def criar_bula(
    session: Session,
    medicamento_id: int,
    id_bula_anvisa: str,
    caminho_pdf: str | None = None,
    ultima_verificacao_anvisa: datetime | None = None,
) -> Bula:
    bula = Bula(
        medicamento_id=medicamento_id,
        id_bula_anvisa=id_bula_anvisa,
        caminho_pdf=caminho_pdf,
        status_processamento_ia=StatusProcessamento.PENDENTE,
        ultima_verificacao_anvisa=ultima_verificacao_anvisa,
    )
    session.add(bula)
    session.flush()
    return bula


def buscar_bula_por_id_anvisa(session: Session, id_bula_anvisa: str) -> Bula | None:
    return session.scalars(
        select(Bula).where(Bula.id_bula_anvisa == id_bula_anvisa)
    ).first()


def atualizar_status_bula(
    session: Session,
    bula_id: int,
    status: StatusProcessamento,
    resposta_bruta: dict | None = None,
    versao_prompt: str | None = None,
    caminho_pdf: str | None = None,
    ultima_verificacao_anvisa: datetime | None = None,
) -> Bula:
    bula = session.get(Bula, bula_id)
    bula.status_processamento_ia = status
    if resposta_bruta is not None:
        bula.resposta_bruta_modelo = resposta_bruta
    if versao_prompt is not None:
        bula.versao_prompt = versao_prompt
    if caminho_pdf is not None:
        bula.caminho_pdf = caminho_pdf
    if ultima_verificacao_anvisa is not None:
        bula.ultima_verificacao_anvisa = ultima_verificacao_anvisa
    session.flush()
    return bula


def listar_bulas_por_status(session: Session, status: StatusProcessamento) -> list[Bula]:
    return list(session.scalars(
        select(Bula).where(Bula.status_processamento_ia == status)
    ).all())


# --- Contra-indicações ---

def criar_contraindicacao(session: Session, bula_id: int, texto: str) -> Contraindicacao:
    ci = Contraindicacao(bula_id=bula_id, texto=texto)
    session.add(ci)
    session.flush()
    return ci


def listar_contraindicacoes_por_bula(session: Session, bula_id: int) -> list[Contraindicacao]:
    return list(session.scalars(
        select(Contraindicacao).where(Contraindicacao.bula_id == bula_id)
    ).all())


# --- Interações ---

def criar_interacao(
    session: Session,
    bula_id: int,
    tipo: str,
    referencia: str,
    efeito: str | None = None,
) -> InteracaoMedicamentosa:
    interacao = InteracaoMedicamentosa(bula_id=bula_id, tipo=tipo, referencia=referencia, efeito=efeito)
    session.add(interacao)
    session.flush()
    return interacao


def listar_interacoes_por_bula(session: Session, bula_id: int) -> list[InteracaoMedicamentosa]:
    return list(session.scalars(
        select(InteracaoMedicamentosa).where(InteracaoMedicamentosa.bula_id == bula_id)
    ).all())


# --- Substâncias do medicamento ---

def criar_substancias_medicamento(session: Session, medicamento_id: int, nome_dcb: str) -> list[SubstanciaMedicamento]:
    """Popula substancias_medicamento via split do nome_dcb por '+'."""
    partes = [p.strip() for p in nome_dcb.split("+") if p.strip()]
    substancias = []
    for nome in partes:
        sub = SubstanciaMedicamento(medicamento_id=medicamento_id, nome=nome)
        session.add(sub)
        substancias.append(sub)
    session.flush()
    return substancias


def listar_substancias_por_medicamento(session: Session, medicamento_id: int) -> list[SubstanciaMedicamento]:
    return list(session.scalars(
        select(SubstanciaMedicamento).where(SubstanciaMedicamento.medicamento_id == medicamento_id)
    ).all())
