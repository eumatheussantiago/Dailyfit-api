"""Testes automáticos da API. Rode com:  pytest"""

import json
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import ia
import seguranca
from database import Base, get_db
from main import app

# Banco temporário em memória: os testes não mexem no dailyfit.db de verdade
engine_teste = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
SessaoTeste = sessionmaker(bind=engine_teste, autocommit=False, autoflush=False)


def get_db_teste():
    db = SessaoTeste()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client():
    Base.metadata.create_all(bind=engine_teste)
    app.dependency_overrides[get_db] = get_db_teste
    seguranca._tentativas.clear()
    yield TestClient(app)
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine_teste)


def criar_usuario(client, email="ana@email.com"):
    """Cria um usuário e devolve (id, cabeçalho com o token de acesso)."""
    resposta = client.post("/usuarios", json={"nome": "Ana", "email": email, "senha": "segredo123"})
    assert resposta.status_code == 201
    dados = resposta.json()
    return dados["id"], {"Authorization": f"Bearer {dados['token']}"}


def test_paginas_abrem(client):
    for pagina in ["/", "/cadastro", "/login", "/formulario", "/painel", "/refeicoes", "/objetivos", "/progresso"]:
        assert client.get(pagina).status_code == 200
    assert client.get("/static/css/style.css").status_code == 200
    assert client.get("/static/js/script.js").status_code == 200
    # endereço antigo da tela Treinos leva para Objetivos
    antiga = client.get("/treinos", follow_redirects=False)
    assert antiga.status_code == 307 and antiga.headers["location"] == "/objetivos"


def test_cabecalhos_de_seguranca(client):
    resposta = client.get("/")
    assert resposta.headers["X-Content-Type-Options"] == "nosniff"
    assert resposta.headers["X-Frame-Options"] == "DENY"
    assert client.get("/static/js/app.js").headers["Cache-Control"] == "no-cache"


def test_cadastro_e_login(client):
    usuario_id, _ = criar_usuario(client, "Ana@Email.com ")

    duplicado = client.post("/usuarios", json={"nome": "Ana", "email": "ana@email.com", "senha": "outra123"})
    assert duplicado.status_code == 400

    login = client.post("/usuarios/login", json={"email": "ANA@email.com", "senha": "segredo123"})
    assert login.status_code == 200
    assert login.json()["id"] == usuario_id
    assert login.json()["perfil_preenchido"] is False
    assert login.json()["token"]

    senha_errada = client.post("/usuarios/login", json={"email": "ana@email.com", "senha": "errada123"})
    assert senha_errada.status_code == 401
    assert client.post("/usuarios/login", json={"email": "x@y.com", "senha": "segredo123"}).status_code == 401


def test_senha_nao_fica_salva_em_texto(client):
    from models.usuario import UsuarioModel

    usuario_id, token = criar_usuario(client)
    resposta = client.get(f"/usuarios/{usuario_id}", headers=token).json()
    assert "senha" not in resposta and "senha_hash" not in resposta

    with SessaoTeste() as db:
        hash_salvo = db.query(UsuarioModel).first().senha_hash
    assert "segredo123" not in hash_salvo
    assert hash_salvo.startswith("pbkdf2_sha256$")


def test_lista_de_usuarios_nao_e_publica(client):
    criar_usuario(client)
    # A rota que listava nome e e-mail de todos foi removida
    assert client.get("/usuarios").status_code == 405


def test_rotas_exigem_login(client):
    usuario_id, _ = criar_usuario(client)

    for rota in ["", "/refeicoes", "/resumo", "/perfil"]:
        assert client.get(f"/usuarios/{usuario_id}{rota}").status_code == 401

    falso = {"Authorization": "Bearer token.falso"}
    assert client.get(f"/usuarios/{usuario_id}/resumo", headers=falso).status_code == 401


def test_token_expirado_e_recusado(client, monkeypatch):
    usuario_id, _ = criar_usuario(client)
    monkeypatch.setattr(seguranca, "VALIDADE_TOKEN", -1)
    vencido = {"Authorization": f"Bearer {seguranca.gerar_token(usuario_id)}"}
    assert client.get(f"/usuarios/{usuario_id}/resumo", headers=vencido).status_code == 401


def test_ninguem_acessa_dados_de_outro_usuario(client):
    ana, token_ana = criar_usuario(client, "ana@email.com")
    bia, token_bia = criar_usuario(client, "bia@email.com")

    refeicao = client.post(
        f"/usuarios/{ana}/refeicoes", json={"nome": "Café", "nao_dieta": False}, headers=token_ana
    ).json()
    client.put(f"/usuarios/{ana}/perfil", json=PERFIL, headers=token_ana)

    # Bia, logada, tentando ler/editar/apagar dados da Ana
    assert client.get(f"/usuarios/{ana}", headers=token_bia).status_code == 403
    assert client.get(f"/usuarios/{ana}/perfil", headers=token_bia).status_code == 403
    assert client.get(f"/usuarios/{ana}/resumo", headers=token_bia).status_code == 403
    assert client.get(f"/usuarios/{ana}/refeicoes", headers=token_bia).status_code == 403
    assert client.delete(f"/usuarios/{ana}/refeicoes/{refeicao['id']}", headers=token_bia).status_code == 403

    # E pelo caminho dela própria, a refeição da Ana não aparece
    assert client.get(f"/usuarios/{bia}/refeicoes/{refeicao['id']}", headers=token_bia).status_code == 404


def test_limite_de_tentativas_de_login(client):
    criar_usuario(client)
    errado = {"email": "ana@email.com", "senha": "errada123"}

    for _ in range(seguranca.MAX_TENTATIVAS):
        assert client.post("/usuarios/login", json=errado).status_code == 401

    bloqueado = client.post("/usuarios/login", json={"email": "ana@email.com", "senha": "segredo123"})
    assert bloqueado.status_code == 429


def test_validacoes(client):
    assert client.post("/usuarios", json={"nome": "A", "email": "a@b.com", "senha": "segredo123"}).status_code == 422
    assert client.post("/usuarios", json={"nome": "Ana", "email": "invalido", "senha": "segredo123"}).status_code == 422
    assert client.post("/usuarios", json={"nome": "Ana", "email": "a@b.com", "senha": "123"}).status_code == 422

    usuario_id, token = criar_usuario(client)
    vazio = client.post(f"/usuarios/{usuario_id}/refeicoes", json={"nome": "   "}, headers=token)
    assert vazio.status_code == 422


def test_crud_de_refeicoes(client):
    usuario_id, token = criar_usuario(client)
    base = f"/usuarios/{usuario_id}/refeicoes"

    criada = client.post(base, json={"nome": "Almoço", "descricao": "Arroz e feijão", "nao_dieta": False}, headers=token)
    assert criada.status_code == 201
    refeicao_id = criada.json()["id"]

    assert client.get(f"{base}/{refeicao_id}", headers=token).json()["nome"] == "Almoço"

    editada = client.put(f"{base}/{refeicao_id}", json={"nome": "Almoço leve", "nao_dieta": True}, headers=token)
    assert editada.status_code == 200
    assert editada.json()["nao_dieta"] is True

    assert client.delete(f"{base}/{refeicao_id}", headers=token).status_code == 204
    assert client.get(f"{base}/{refeicao_id}", headers=token).status_code == 404


def test_horario_da_refeicao_vem_com_fuso(client):
    """Antes, o horário aparecia 3 horas adiantado no navegador."""
    usuario_id, token = criar_usuario(client)
    criada = client.post(f"/usuarios/{usuario_id}/refeicoes", json={"nome": "Café"}, headers=token).json()

    data_hora = datetime.fromisoformat(criada["data_hora"].replace("Z", "+00:00"))
    assert data_hora.tzinfo is not None
    assert abs(datetime.now(timezone.utc) - data_hora) < timedelta(minutes=1)


def test_horario_informado_pela_pessoa(client):
    """A refeição pode ter a hora em que foi feita, não só a do registro."""
    usuario_id, token = criar_usuario(client)
    base = f"/usuarios/{usuario_id}/refeicoes"
    duas_horas_atras = datetime.now(timezone.utc) - timedelta(hours=2)

    # com fuso de Brasília: a API guarda e devolve o mesmo instante, em UTC
    em_brasilia = duas_horas_atras.astimezone(timezone(timedelta(hours=-3))).isoformat()
    criada = client.post(base, json={"nome": "Café", "data_hora": em_brasilia}, headers=token)
    assert criada.status_code == 201
    salva = datetime.fromisoformat(criada.json()["data_hora"].replace("Z", "+00:00"))
    assert abs(salva - duas_horas_atras) < timedelta(seconds=1)

    # ao editar sem mandar o horário, ele continua o mesmo
    refeicao_id = criada.json()["id"]
    editada = client.put(f"{base}/{refeicao_id}", json={"nome": "Café da manhã"}, headers=token).json()
    assert editada["data_hora"] == criada.json()["data_hora"]

    # ao editar mandando outro horário, ele muda
    ontem = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    editada = client.put(f"{base}/{refeicao_id}", json={"nome": "Café", "data_hora": ontem}, headers=token).json()
    assert editada["data_hora"] != criada.json()["data_hora"]

    # recusados: no futuro, mais de 30 dias atrás e sem fuso
    amanha = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    antigo = (datetime.now(timezone.utc) - timedelta(days=40)).isoformat()
    for data_hora in [amanha, antigo, "2026-10-23T12:30:00"]:
        resposta = client.post(base, json={"nome": "Café", "data_hora": data_hora}, headers=token)
        assert resposta.status_code == 422, data_hora


def test_resumo(client):
    usuario_id, token = criar_usuario(client)
    base = f"/usuarios/{usuario_id}/refeicoes"

    for nome, fora in [("Café", False), ("Lanche", False), ("Pizza", True), ("Almoço", False), ("Jantar", False), ("Ceia", False)]:
        client.post(base, json={"nome": nome, "nao_dieta": fora}, headers=token)

    resumo = client.get(f"/usuarios/{usuario_id}/resumo", headers=token).json()
    assert resumo == {
        "total_refeicoes_cadastradas": 6,
        "total_refeicoes_dentro_da_dieta": 5,
        "total_refeicoes_fora_da_dieta": 1,
        "melhor_sequencia_de_refeicoes_dentro_da_dieta": 3,
    }


PERFIL = {
    "objetivo": "emagrecimento",
    "sexo": "feminino",
    "idade": 25,
    "altura": 165,
    "peso_atual": 70.5,
    "peso_meta": 64,
    "atividade": "levemente_ativo",
    "tipo_alimentacao": "variada",
    "restricoes": "Lactose",
    "preferencias": "",
    "refeicoes_por_dia": 4,
    "horario_cafe": "07:30",
    "horario_almoco": "12:00",
    "horario_jantar": None,
    "dificuldades_rotina": "Pouco tempo para cozinhar",
}


def test_formulario_inicial(client):
    usuario_id, token = criar_usuario(client)
    url = f"/usuarios/{usuario_id}/perfil"

    assert client.get(url, headers=token).status_code == 404

    salvo = client.put(url, json=PERFIL, headers=token)
    assert salvo.status_code == 200
    assert salvo.json()["preferencias"] is None  # texto vazio vira vazio no banco

    # Responder de novo atualiza em vez de duplicar
    atualizado = client.put(url, json={**PERFIL, "peso_atual": 69}, headers=token)
    assert atualizado.json()["peso_atual"] == 69
    # números calculados vêm junto (detalhes em tests/test_saude.py)
    indicadores = atualizado.json()["indicadores"]
    assert indicadores["imc"] == 25.3 and indicadores["faixa_imc"] == "Sobrepeso"
    assert indicadores["semanas_ate_meta"] == 10  # 69 → 64 kg a 0,5 kg por semana
    assert client.get(url, headers=token).json()["peso_atual"] == 69

    login = client.post("/usuarios/login", json={"email": "ana@email.com", "senha": "segredo123"})
    assert login.json()["perfil_preenchido"] is True

    assert client.put(url, json={**PERFIL, "objetivo": "voar"}, headers=token).status_code == 422
    assert client.put(url, json={**PERFIL, "horario_cafe": "25:00"}, headers=token).status_code == 422


def test_banco_antigo_ganha_coluna_de_senha(tmp_path):
    """Quem já tinha um dailyfit.db sem a coluna de senha não precisa apagá-lo."""
    import sqlite3
    from sqlalchemy import create_engine, inspect
    import database

    caminho = tmp_path / "antigo.db"
    conexao = sqlite3.connect(caminho)
    conexao.execute("CREATE TABLE usuarios (id INTEGER PRIMARY KEY, nome VARCHAR(100), email VARCHAR(255))")
    conexao.commit()
    conexao.close()

    engine_original = database.engine
    database.engine = create_engine(f"sqlite:///{caminho}")
    try:
        database.criar_tabelas()
        colunas = {c["name"] for c in inspect(database.engine).get_columns("usuarios")}
        assert "senha_hash" in colunas
        assert "perfis" in inspect(database.engine).get_table_names()
        indices = {i["name"] for i in inspect(database.engine).get_indexes("refeicoes")}
        assert "ix_refeicoes_usuario_data" in indices
    finally:
        database.engine.dispose()
        database.engine = engine_original


ACEITE = {"consentimento": True}
DICA = {"titulo": "Café no horário", "texto": "Tome o café às 7h30, como você planejou."}


def preparar_dicas(client, monkeypatch, gerar):
    """Usuário com formulário respondido, chave de teste e a IA trocada por uma função falsa."""
    usuario_id, token = criar_usuario(client)
    client.put(f"/usuarios/{usuario_id}/perfil", json=PERFIL, headers=token)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "chave-de-teste")
    monkeypatch.setattr(ia, "gerar_dicas", gerar)
    return f"/usuarios/{usuario_id}/dicas", usuario_id, token


def test_dicas_desligadas_sem_chave(client, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    usuario_id, token = criar_usuario(client)
    url = f"/usuarios/{usuario_id}/dicas"
    assert client.get(url, headers=token).json() == {"ligadas": False, "dicas": [], "criado_em": None, "proxima_em": None}
    assert client.post(url, json=ACEITE, headers=token).status_code == 503


def test_dicas_com_ia(client, monkeypatch):
    enviados = []

    def ia_falsa(dados):
        enviados.append(dados)
        return [DICA]

    url, usuario_id, token = preparar_dicas(client, monkeypatch, ia_falsa)
    client.post(f"/usuarios/{usuario_id}/refeicoes", json={"nome": "Lanche", "nao_dieta": True}, headers=token)

    gerada = client.post(url, json=ACEITE, headers=token)
    assert gerada.status_code == 200
    assert gerada.json()["ligadas"] is True and gerada.json()["dicas"] == [DICA]
    assert gerada.json()["criado_em"].endswith("Z")

    # a IA recebe formulário, números e o resumo da semana, nunca nome nem e-mail
    texto = json.dumps(enviados[0], ensure_ascii=False)
    assert "ana@email.com" not in texto and "Ana" not in texto
    assert enviados[0]["formulario"]["restricoes"] == "Lactose"
    assert enviados[0]["numeros"]["imc"] == 25.9
    assert enviados[0]["ultimos_7_dias"]["fora_da_dieta"] == 1

    # fica guardada; gerar de novo no mesmo dia é recusado sem chamar a IA
    assert client.get(url, headers=token).json()["dicas"] == [DICA]
    assert client.post(url, json=ACEITE, headers=token).status_code == 429
    assert len(enviados) == 1

    # só o dono vê
    _, token_bia = criar_usuario(client, "bia@email.com")
    assert client.get(url, headers=token_bia).status_code == 403


def test_dicas_erro_da_ia_e_limites(client, monkeypatch):
    def ia_fora_do_ar(dados):
        raise ia.ErroDicas("O serviço de IA não respondeu agora. Tente de novo mais tarde.")

    url, usuario_id, token = preparar_dicas(client, monkeypatch, ia_fora_do_ar)
    falhou = client.post(url, json=ACEITE, headers=token)
    assert falhou.status_code == 503 and "não respondeu" in falhou.json()["detail"]
    assert client.get(url, headers=token).json()["dicas"] == []  # nada foi salvo

    monkeypatch.setenv("DICAS_LIMITE_DIA", "0")
    assert "limite" in client.post(url, json=ACEITE, headers=token).json()["detail"]

    # sem formulário respondido
    sem_perfil, token_sem = criar_usuario(client, "caio@email.com")
    assert client.post(f"/usuarios/{sem_perfil}/dicas", json=ACEITE, headers=token_sem).status_code == 400


def test_ia_usa_haiku_e_trata_recusa(monkeypatch):
    chamadas = []

    class Recusa:
        stop_reason = "refusal"
        parsed_output = None

    class ClienteFalso:
        def __init__(self, **opcoes):
            self.messages = self

        def parse(self, **pedido):
            chamadas.append(pedido)
            return Recusa()

    monkeypatch.setattr(ia.anthropic, "Anthropic", ClienteFalso)
    with pytest.raises(ia.ErroDicas):
        ia.gerar_dicas({"formulario": {"objetivo": "emagrecimento"}})
    assert chamadas[0]["model"] == "claude-haiku-5-5"
    assert chamadas[0]["output_format"] is ia.Dicas
    assert "emagrecimento" in chamadas[0]["messages"][0]["content"]


def test_dicas_exigem_consentimento_e_maioridade(client, monkeypatch):
    url, usuario_id, token = preparar_dicas(client, monkeypatch, lambda dados: [DICA])
    sem_aceite = client.post(url, json={}, headers=token)
    assert sem_aceite.status_code == 400 and "concorda" in sem_aceite.json()["detail"]

    client.put(f"/usuarios/{usuario_id}/perfil", json={**PERFIL, "idade": 16}, headers=token)
    menor = client.post(url, json=ACEITE, headers=token)
    assert menor.status_code == 400 and "18 anos" in menor.json()["detail"]


def test_dicas_tentativas_contam_no_limite(client, monkeypatch):
    def ia_fora_do_ar(dados):
        raise ia.ErroDicas("O serviço de IA não respondeu agora. Tente de novo mais tarde.")

    url, usuario_id, token = preparar_dicas(client, monkeypatch, ia_fora_do_ar)
    # 3 falhas seguidas e a quarta tentativa já é recusada sem chamar a IA
    assert [client.post(url, json=ACEITE, headers=token).status_code for _ in range(4)] == [503, 503, 503, 429]

    # a falha também conta no limite do site
    monkeypatch.setenv("DICAS_LIMITE_DIA", "3")
    bia_id, token_bia = criar_usuario(client, "bia@email.com")
    client.put(f"/usuarios/{bia_id}/perfil", json=PERFIL, headers=token_bia)
    bia = client.post(f"/usuarios/{bia_id}/dicas", json=ACEITE, headers=token_bia)
    assert bia.status_code == 503 and "limite" in bia.json()["detail"]


def test_dicas_em_andamento_bloqueiam_clique_duplo(client, monkeypatch):
    from datetime import datetime as dt

    url, usuario_id, token = preparar_dicas(client, monkeypatch, lambda dados: [DICA])
    # simula uma geração ainda em andamento (reserva gravada há poucos segundos)
    db = next(get_db_teste())
    from models.dica import DicaModel
    from database import agora_utc
    db.add(DicaModel(usuario_id=usuario_id, conteudo="", criado_em=agora_utc()))
    db.commit()
    resposta = client.post(url, json=ACEITE, headers=token)
    assert resposta.status_code == 429 and "sendo geradas" in resposta.json()["detail"]
    assert client.get(url, headers=token).json()["dicas"] == []  # reserva não aparece como dica


def test_dados_para_ia_sinalizam_quem_precisa_de_cuidado(client, monkeypatch):
    enviados = []
    url, usuario_id, token = preparar_dicas(client, monkeypatch, lambda dados: enviados.append(dados) or [DICA])

    # 19 anos com meta de IMC 16,5: saude.py não classifica a faixa, mas o sinal vale em qualquer idade
    client.put(f"/usuarios/{usuario_id}/perfil", json={**PERFIL, "idade": 19, "peso_meta": 45}, headers=token)
    client.post(url, json=ACEITE, headers=token)
    assert enviados[-1]["precisa_cuidado"] is True

    # já abaixo do peso, sem meta
    _, token_bia = criar_usuario(client, "bia@email.com")
    bia_id = client.post("/usuarios/login", json={"email": "bia@email.com", "senha": "segredo123"}).json()["id"]
    client.put(f"/usuarios/{bia_id}/perfil", json={**PERFIL, "peso_atual": 48, "peso_meta": None}, headers=token_bia)
    client.post(f"/usuarios/{bia_id}/dicas", json=ACEITE, headers=token_bia)
    assert enviados[-1]["precisa_cuidado"] is True

    # PERFIL padrão (IMC 25,9, meta 64 kg = IMC 23,5) não precisa
    _, token_caio = criar_usuario(client, "caio@email.com")
    caio_id = client.post("/usuarios/login", json={"email": "caio@email.com", "senha": "segredo123"}).json()["id"]
    client.put(f"/usuarios/{caio_id}/perfil", json=PERFIL, headers=token_caio)
    client.post(f"/usuarios/{caio_id}/dicas", json=ACEITE, headers=token_caio)
    assert enviados[-1]["precisa_cuidado"] is False


def test_ia_resposta_cortada_ou_vazia_vira_erro_amigavel(monkeypatch):
    from pydantic import ValidationError

    class Vazia:
        stop_reason = "end_turn"
        parsed_output = ia.Dicas(dicas=[])

    respostas = []

    class ClienteFalso:
        def __init__(self, **opcoes):
            self.messages = self

        def parse(self, **pedido):
            resposta = respostas.pop(0)
            if isinstance(resposta, Exception):
                raise resposta
            return resposta

    monkeypatch.setattr(ia.anthropic, "Anthropic", ClienteFalso)
    try:
        ia.Dicas.model_validate_json('{"dicas": [{"titulo": "Café')  # JSON cortado
    except ValidationError as cortado:
        respostas.append(cortado)
    respostas.append(Vazia())

    for _ in range(2):
        with pytest.raises(ia.ErroDicas):
            ia.gerar_dicas({"formulario": {}})
