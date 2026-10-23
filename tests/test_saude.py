from saude import calcular_indicadores, faixa_imc


def indicadores(**dados):
    base = {"sexo": "masculino", "idade": 30, "altura": 175, "peso_atual": 70, "peso_meta": None, "atividade": "moderadamente_ativo"}
    return calcular_indicadores(**{**base, **dados})


def test_adulto_sem_meta():
    n = indicadores()
    assert n["imc"] == 22.9 and n["faixa_imc"] == "Peso normal"
    assert (n["peso_saudavel_min"], n["peso_saudavel_max"]) == (56.7, 76.3)
    # basal = 10×70 + 6,25×175 − 5×30 + 5 = 1648,75; × 1,55 = 2555,6 → 2560
    assert n["gasto_calorico"] == 2560
    assert n["agua_litros"] == 2.5
    assert n["imc_meta"] is None and n["semanas_ate_meta"] is None and n["meta_abaixo_do_saudavel"] is False


def test_meta_e_alerta_abaixo_do_saudavel():
    # mulher, 165 cm: basal = 600 + 1031,25 − 125 − 161 = 1345,25; × 1,2 = 1614,3 → 1610
    n = indicadores(sexo="feminino", idade=25, altura=165, peso_atual=60, peso_meta=48, atividade="sedentario")
    assert n["gasto_calorico"] == 1610
    assert n["imc_meta"] == 17.6 and n["meta_abaixo_do_saudavel"] is True
    assert n["semanas_ate_meta"] == 24  # 12 kg a 0,5 kg por semana

    ganhar = indicadores(peso_meta=73.2)  # 3,2 kg → 6,4 semanas → 7
    assert ganhar["semanas_ate_meta"] == 7 and ganhar["meta_abaixo_do_saudavel"] is False
    assert indicadores(peso_meta=70)["semanas_ate_meta"] == 0


def test_menores_de_idade_nao_recebem_faixa_nem_gasto():
    jovem = indicadores(idade=16)
    assert jovem["imc"] == 22.9
    assert jovem["faixa_imc"] is None  # a OMS usa tabela por idade abaixo de 20 anos
    assert jovem["gasto_calorico"] is None  # Mifflin-St Jeor só a partir de 18
    assert indicadores(idade=19, peso_meta=50)["meta_abaixo_do_saudavel"] is False


def test_limites_das_faixas_e_dados_absurdos():
    assert faixa_imc(18.4) == "Abaixo do peso"
    assert faixa_imc(18.5) == "Peso normal"
    assert faixa_imc(25.0) == "Sobrepeso"
    assert faixa_imc(30.0) == "Obesidade grau I"
    assert faixa_imc(40.0) == "Obesidade grau III"
    # basal = 10×1 + 6,25×50 − 5×100 − 161 = −338,5: sem gasto, em vez de um número negativo
    assert indicadores(sexo="feminino", altura=50, peso_atual=1, idade=100)["gasto_calorico"] is None
