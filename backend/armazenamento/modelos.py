import enum
from datetime import datetime
from typing import Literal

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class StatusProcessamento(str, enum.Enum):
    PENDENTE = "PENDENTE"
    PROCESSADO = "PROCESSADO"
    ERRO = "ERRO"


class Medicamento(Base):
    __tablename__ = "medicamentos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome_comercial: Mapped[str] = mapped_column(String(500), nullable=False)
    nome_dcb: Mapped[str | None] = mapped_column(String(500))
    substancia_ativa: Mapped[str | None] = mapped_column(String(500))
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    bulas: Mapped[list["Bula"]] = relationship(back_populates="medicamento")
    substancias: Mapped[list["SubstanciaMedicamento"]] = relationship(back_populates="medicamento")


class Bula(Base):
    __tablename__ = "bulas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    medicamento_id: Mapped[int] = mapped_column(
        ForeignKey("medicamentos.id"), nullable=False
    )
    id_bula_anvisa: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)
    caminho_pdf: Mapped[str | None] = mapped_column(String(1000))
    status_processamento_ia: Mapped[StatusProcessamento] = mapped_column(
        Enum(StatusProcessamento), default=StatusProcessamento.PENDENTE, nullable=False
    )
    resposta_bruta_modelo: Mapped[dict | None] = mapped_column(JSONB)
    versao_prompt: Mapped[str | None] = mapped_column(String(20))
    ultima_verificacao_anvisa: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    medicamento: Mapped["Medicamento"] = relationship(back_populates="bulas")
    contraindicacoes: Mapped[list["Contraindicacao"]] = relationship(
        back_populates="bula"
    )
    interacoes: Mapped[list["InteracaoMedicamentosa"]] = relationship(
        back_populates="bula"
    )


class Contraindicacao(Base):
    __tablename__ = "contraindicacoes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bula_id: Mapped[int] = mapped_column(ForeignKey("bulas.id"), nullable=False)
    texto: Mapped[str] = mapped_column(Text, nullable=False)

    bula: Mapped["Bula"] = relationship(back_populates="contraindicacoes")


class InteracaoMedicamentosa(Base):
    __tablename__ = "interacoes_medicamentosas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bula_id: Mapped[int] = mapped_column(ForeignKey("bulas.id"), nullable=False)
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    referencia: Mapped[str] = mapped_column(String(500), nullable=False)
    efeito: Mapped[str | None] = mapped_column(Text, nullable=True)

    bula: Mapped["Bula"] = relationship(back_populates="interacoes")


class SubstanciaMedicamento(Base):
    __tablename__ = "substancias_medicamento"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    medicamento_id: Mapped[int] = mapped_column(ForeignKey("medicamentos.id"), nullable=False)
    nome: Mapped[str] = mapped_column(String(500), nullable=False)

    medicamento: Mapped["Medicamento"] = relationship(back_populates="substancias")
