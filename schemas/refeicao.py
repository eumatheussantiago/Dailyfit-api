from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RefeicaoCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=100)
    descricao: Optional[str] = Field(default=None, max_length=500)
    nao_dieta: bool = False

    @field_validator("nome")
    @classmethod
    def limpar_nome(cls, valor: str) -> str:
        valor = valor.strip()
        if not valor:
            raise ValueError("Informe o nome da refeição")
        return valor

    @field_validator("descricao")
    @classmethod
    def limpar_descricao(cls, valor: Optional[str]) -> Optional[str]:
        if valor is None:
            return None
        return valor.strip() or None


class RefeicaoResponse(BaseModel):
    id: int
    usuario_id: int
    nome: str
    descricao: Optional[str]
    data_hora: datetime
    nao_dieta: bool

    model_config = ConfigDict(from_attributes=True)
