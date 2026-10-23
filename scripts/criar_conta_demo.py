"""Cria (ou completa) uma conta de demonstração com uma semana de refeições.

Uso, para a apresentação (rode alguns minutos antes, o site grátis "dorme"):

    python scripts/criar_conta_demo.py https://dailyfit-037t.onrender.com demo@dailyfit.app

A senha é perguntada na hora (não fica no código nem no histórico do terminal).
Usa só a API pública do site: cadastro (ou login, se a conta já existir), formulário
inicial e refeições com horário dos últimos 7 dias (campo "data_hora").
"""

import getpass
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta

PERFIL = {
    "objetivo": "emagrecimento",
    "sexo": "feminino",
    "idade": 24,
    "altura": 165,
    "peso_atual": 72.5,
    "peso_meta": 66,
    "atividade": "levemente_ativo",
    "tipo_alimentacao": "variada",
    "restricoes": "Lactose",
    "preferencias": "Frango, arroz integral, frutas",
    "refeicoes_por_dia": 4,
    "horario_cafe": "07:30",
    "horario_almoco": "12:30",
    "horario_jantar": "19:30",
    "dificuldades_rotina": "Pulo o almoço quando o trabalho aperta",
}

# dias atrás → refeições do dia: (nome, hora, fora da dieta?)
SEMANA = {
    6: [("Café da manhã", "07:40", False), ("Almoço", "12:50", False), ("Jantar", "20:10", False)],
    5: [("Café da manhã", "07:30", False), ("Almoço", "13:20", True), ("Lanche", "16:00", False), ("Jantar", "19:45", False)],
    4: [("Café da manhã", "08:00", False), ("Jantar", "21:00", True)],
    3: [("Café da manhã", "07:35", False), ("Almoço", "12:30", False), ("Lanche", "15:45", False), ("Jantar", "19:30", False)],
    2: [("Café da manhã", "07:30", False), ("Almoço", "12:40", False), ("Jantar", "19:50", False)],
    1: [("Café da manhã", "07:45", False), ("Almoço", "12:35", False), ("Lanche da tarde", "16:10", True), ("Jantar", "20:00", False)],
    0: [("Café da manhã", "07:30", False)],
}


def chamar(base, metodo, caminho, corpo=None, token=None):
    pedido = urllib.request.Request(
        base + caminho,
        method=metodo,
        data=json.dumps(corpo).encode() if corpo is not None else None,
        headers={"Content-Type": "application/json", **({"Authorization": f"Bearer {token}"} if token else {})},
    )
    try:
        with urllib.request.urlopen(pedido, timeout=90) as resposta:  # 1º acesso acorda o site (~1 min)
            return resposta.status, json.loads(resposta.read() or b"null")
    except urllib.error.HTTPError as erro:
        return erro.code, json.loads(erro.read() or b"null")


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    base, email = sys.argv[1].rstrip("/"), sys.argv[2]
    senha = getpass.getpass(f"Senha para {email} (mínimo 6 caracteres): ")

    status, conta = chamar(base, "POST", "/usuarios", {"nome": "Maria Demonstração", "email": email, "senha": senha})
    if status == 201:
        print("Conta criada.")
        if conta.get("codigo_recuperacao"):
            print(f"Código de recuperação (guarde): {conta['codigo_recuperacao']}")
    else:
        status, conta = chamar(base, "POST", "/usuarios/login", {"email": email, "senha": senha})
        if status != 200:
            sys.exit(f"Não deu para criar nem entrar na conta: {conta}")
        print("A conta já existia: entrei com ela.")
    uid, token = conta["id"], conta["token"]

    status, _ = chamar(base, "PUT", f"/usuarios/{uid}/perfil", PERFIL, token)
    print("Formulário inicial salvo." if status == 200 else f"Falha no formulário: {status}")

    _, existentes = chamar(base, "GET", f"/usuarios/{uid}/refeicoes", token=token)
    if existentes:
        print(f"A conta já tem {len(existentes)} refeições: não adicionei outras.")
        return

    agora = datetime.now().astimezone()  # horário local deste computador, com fuso
    criadas = 0
    for dias, refeicoes in SEMANA.items():
        for nome, hora, fora in refeicoes:
            h, m = map(int, hora.split(":"))
            quando = (agora - timedelta(days=dias)).replace(hour=h, minute=m, second=0, microsecond=0)
            if quando > agora:
                continue  # hoje, só o que já passou
            corpo = {"nome": nome, "nao_dieta": fora, "data_hora": quando.isoformat()}
            status, _ = chamar(base, "POST", f"/usuarios/{uid}/refeicoes", corpo, token)
            criadas += status == 201
    print(f"{criadas} refeições criadas nos últimos 7 dias. Pronto: entre com {email} no site.")


if __name__ == "__main__":
    main()
