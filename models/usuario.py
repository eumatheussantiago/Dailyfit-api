from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class UsuarioModel(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    nome: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)

    # Ao apagar um usuário, as refeições dele são apagadas junto
    refeicoes: Mapped[list["RefeicaoModel"]] = relationship(
        back_populates="usuario",
        cascade="all, delete-orphan",
    )
