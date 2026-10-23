from typing import Optional

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class UsuarioModel(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    nome: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    senha_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Ao apagar um usuário, as refeições, o perfil e as dicas dele são apagados junto
    refeicoes: Mapped[list["RefeicaoModel"]] = relationship(
        back_populates="usuario",
        cascade="all, delete-orphan",
    )
    perfil: Mapped[Optional["PerfilModel"]] = relationship(
        back_populates="usuario",
        cascade="all, delete-orphan",
        uselist=False,
    )
    dicas: Mapped[list["DicaModel"]] = relationship(
        back_populates="usuario",
        cascade="all, delete-orphan",
    )

    @property
    def perfil_preenchido(self) -> bool:
        return self.perfil is not None
