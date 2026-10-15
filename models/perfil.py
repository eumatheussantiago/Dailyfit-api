from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class PerfilModel(Base):
    """Respostas do formulário inicial (formulario.html). Um perfil por usuário."""

    __tablename__ = "perfis"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )

    # Etapa 1 - sobre você
    objetivo: Mapped[str] = mapped_column(String(30))
    sexo: Mapped[str] = mapped_column(String(20))
    idade: Mapped[int] = mapped_column(Integer)
    altura: Mapped[float] = mapped_column(Float)          # em cm
    peso_atual: Mapped[float] = mapped_column(Float)      # em kg
    peso_meta: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    atividade: Mapped[str] = mapped_column(String(30))

    # Etapa 2 - alimentação
    tipo_alimentacao: Mapped[str] = mapped_column(String(30))
    restricoes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    preferencias: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    refeicoes_por_dia: Mapped[int] = mapped_column(Integer)

    # Etapa 3 - rotina
    horario_cafe: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)
    horario_almoco: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)
    horario_jantar: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)
    dificuldades_rotina: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )

    usuario: Mapped["UsuarioModel"] = relationship(back_populates="perfil")
