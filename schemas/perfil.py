import re
from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

from saude import calcular_indicadores

# Valores aceitos = os "value" dos campos em templates/formulario.html
Objetivo = Literal["emagrecimento", "ganho_massa", "manutencao", "reeducacao"]
Sexo = Literal["masculino", "feminino"]
Atividade = Literal[
    "sedentario",
    "levemente_ativo",
    "moderadamente_ativo",
    "muito_ativo",
    "extremamente_ativo",
]
TipoAlimentacao = Literal["variada", "vegetariana", "vegana", "outra"]


class PerfilBase(BaseModel):
    objetivo: Objetivo
    sexo: Sexo
    idade: int = Field(ge=1, le=120)
    altura: float = Field(gt=0, le=300)       # cm
    peso_atual: float = Field(gt=0, le=500)   # kg
    peso_meta: Optional[float] = Field(default=None, gt=0, le=500)
    atividade: Atividade

    tipo_alimentacao: TipoAlimentacao
    restricoes: Optional[str] = Field(default=None, max_length=1000)
    preferencias: Optional[str] = Field(default=None, max_length=1000)
    refeicoes_por_dia: int = Field(ge=1, le=12)

    horario_cafe: Optional[str] = None
    horario_almoco: Optional[str] = None
    horario_jantar: Optional[str] = None
    dificuldades_rotina: Optional[str] = Field(default=None, max_length=1000)

    @field_validator("restricoes", "preferencias", "dificuldades_rotina")
    @classmethod
    def texto_vazio_vira_nulo(cls, valor: Optional[str]) -> Optional[str]:
        if valor is None:
            return None
        return valor.strip() or None

    @field_validator("horario_cafe", "horario_almoco", "horario_jantar")
    @classmethod
    def validar_horario(cls, valor: Optional[str]) -> Optional[str]:
        if not valor:
            return None
        if not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", valor):
            raise ValueError("Horário inválido (use HH:MM)")
        return valor


class PerfilSalvar(PerfilBase):
    pass


class Indicadores(BaseModel):
    """Estimativas calculadas a partir do formulário (ver saude.py)."""

    imc: float
    faixa_imc: Optional[str]          # só a partir de 20 anos
    peso_saudavel_min: float          # kg, IMC 18,5 para a altura
    peso_saudavel_max: float          # kg, IMC 24,9 para a altura
    gasto_calorico: Optional[int]     # kcal por dia; só a partir de 18 anos
    agua_litros: float
    imc_meta: Optional[float]
    meta_abaixo_do_saudavel: bool
    semanas_ate_meta: Optional[int]   # no ritmo de 0,5 kg por semana


class PerfilResponse(PerfilBase):
    usuario_id: int
    atualizado_em: datetime

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def indicadores(self) -> Indicadores:
        return Indicadores(**calcular_indicadores(
            sexo=self.sexo,
            idade=self.idade,
            altura=self.altura,
            peso_atual=self.peso_atual,
            peso_meta=self.peso_meta,
            atividade=self.atividade,
        ))

    @field_validator("atualizado_em")
    @classmethod
    def em_utc(cls, valor: datetime) -> datetime:
        return valor if valor.tzinfo else valor.replace(tzinfo=timezone.utc)
