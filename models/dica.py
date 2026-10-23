from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base, agora_utc


class DicaModel(Base):
    """Dicas geradas pela IA para um usuário (uma geração por linha)."""

    __tablename__ = "dicas"
    __table_args__ = (
        # "última geração do usuário X" e "gerações das últimas 24 h"
        Index("ix_dicas_usuario_criado", "usuario_id", "criado_em"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"),
        index=True,
    )
    conteudo: Mapped[str] = mapped_column(Text)  # JSON: [{"titulo": ..., "texto": ...}, ...]
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=agora_utc)

    usuario: Mapped["UsuarioModel"] = relationship(back_populates="dicas")
