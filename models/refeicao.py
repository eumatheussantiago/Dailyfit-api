from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class RefeicaoModel(Base):
    __tablename__ = "refeicoes"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"),
        index=True,
    )
    nome: Mapped[str] = mapped_column(String(100))
    descricao: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    data_hora: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    nao_dieta: Mapped[bool] = mapped_column(Boolean, default=False)

    usuario: Mapped["UsuarioModel"] = relationship(back_populates="refeicoes")
