"""Números de saúde calculados a partir do formulário inicial (estimativas gerais).

- IMC (peso ÷ altura²) e faixa da OMS, só para adultos (20 anos ou mais: abaixo
  disso a OMS avalia o IMC por tabela de idade, então mostramos só o número).
- Faixa de peso saudável para a altura: IMC de 18,5 a 24,9.
- Gasto calórico do dia: taxa metabólica basal de Mifflin-St Jeor × fator do nível
  de atividade (só a partir de 18 anos, faixa em que a fórmula foi validada).
- Água: 35 ml por kg de peso.
- Prazo até a meta de peso no ritmo de 0,5 kg por semana.

Não substituem a avaliação de um nutricionista ou médico (a tela avisa).
"""

import math
from typing import Optional

# Mesmas chaves do campo "atividade" do formulário (schemas/perfil.py)
FATOR_ATIVIDADE = {
    "sedentario": 1.2,
    "levemente_ativo": 1.375,
    "moderadamente_ativo": 1.55,
    "muito_ativo": 1.725,
    "extremamente_ativo": 1.9,
}

# Faixas de IMC da OMS para adultos: (limite superior, nome)
FAIXAS_IMC = (
    (18.5, "Abaixo do peso"),
    (25.0, "Peso normal"),
    (30.0, "Sobrepeso"),
    (35.0, "Obesidade grau I"),
    (40.0, "Obesidade grau II"),
    (math.inf, "Obesidade grau III"),
)

RITMO_KG_POR_SEMANA = 0.5


def faixa_imc(imc: float) -> str:
    return next(nome for limite, nome in FAIXAS_IMC if imc < limite)


def calcular_indicadores(
    *,
    sexo: str,
    idade: int,
    altura: float,
    peso_atual: float,
    peso_meta: Optional[float],
    atividade: str,
) -> dict:
    """altura em cm, pesos em kg."""
    metros2 = (altura / 100) ** 2
    imc = round(peso_atual / metros2, 1)  # a faixa usa o mesmo número que aparece na tela

    indicadores = {
        "imc": imc,
        "faixa_imc": faixa_imc(imc) if idade >= 20 else None,
        "peso_saudavel_min": round(18.5 * metros2, 1),
        "peso_saudavel_max": round(24.9 * metros2, 1),
        "gasto_calorico": None,
        "agua_litros": round(peso_atual * 0.035, 1),
        "imc_meta": None,
        "meta_abaixo_do_saudavel": False,
        "semanas_ate_meta": None,
    }

    if idade >= 18:
        basal = 10 * peso_atual + 6.25 * altura - 5 * idade + (5 if sexo == "masculino" else -161)
        if basal > 0:  # dados absurdos (ex.: 1 kg) não viram um número negativo na tela
            indicadores["gasto_calorico"] = int(round(basal * FATOR_ATIVIDADE[atividade], -1))

    if peso_meta:
        imc_meta = round(peso_meta / metros2, 1)
        indicadores["imc_meta"] = imc_meta
        indicadores["meta_abaixo_do_saudavel"] = idade >= 20 and imc_meta < 18.5
        indicadores["semanas_ate_meta"] = math.ceil(round(abs(peso_meta - peso_atual), 1) / RITMO_KG_POR_SEMANA)

    return indicadores
