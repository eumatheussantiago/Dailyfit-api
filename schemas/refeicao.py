from datetime import datetime, timedelta, timezone
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from database import agora_utc

# Hora da refeição informada pela pessoa: até alguns minutos à frente (relógio do celular
# adiantado) e no máximo 30 dias para trás (lançar um dia esquecido)
TOLERANCIA_FUTURO = timedelta(minutes=5)
LIMITE_PASSADO = timedelta(days=30)


class RefeicaoCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=100)
    descricao: Optional[str] = Field(default=None, max_length=500)
    nao_dieta: bool = False
    # Opcional: sem ela, vale a hora do registro (ao criar) ou a hora que já estava (ao editar)
    data_hora: Optional[datetime] = None

    @field_validator("data_hora")
    @classmethod
    def validar_data_hora(cls, valor: Optional[datetime]) -> Optional[datetime]:
        if valor is None:
            return None
        if valor.tzinfo is None:
            # Sem fuso não dá para saber se 12:00 é no Brasil ou em UTC
            raise ValueError("Informe o horário com fuso (ex.: 2026-10-23T12:30:00-03:00)")
        # O banco guarda em UTC sem fuso (ver agora_utc)
        valor = valor.astimezone(timezone.utc).replace(tzinfo=None)
        agora = agora_utc()
        if valor > agora + TOLERANCIA_FUTURO:
            raise ValueError("O horário não pode ser no futuro")
        if valor < agora - LIMITE_PASSADO:
            raise ValueError("Só dá para registrar refeições dos últimos 30 dias")
        return valor

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

    @field_validator("data_hora")
    @classmethod
    def em_utc(cls, valor: datetime) -> datetime:
        # O banco guarda em UTC sem fuso; informa o fuso para o navegador converter
        return valor if valor.tzinfo else valor.replace(tzinfo=timezone.utc)
