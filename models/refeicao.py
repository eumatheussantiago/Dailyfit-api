from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base, agora_utc


class RefeicaoModel(Base):
    __tablename__ = "refeicoes"
    __table_args__ = (
        # Acelera "refeições do usuário X em ordem de data" (lista e resumo)
        Index("ix_refeicoes_usuario_data", "usuario_id", "data_hora"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"),
        index=True,
    )
    nome: Mapped[str] = mapped_column(String(100))
    descricao: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    data_hora: Mapped[datetime] = mapped_column(DateTime, default=agora_utc)
    nao_dieta: Mapped[bool] = mapped_column(Boolean, default=False)

    usuario: Mapped["UsuarioModel"] = relationship(back_populates="refeicoes")
