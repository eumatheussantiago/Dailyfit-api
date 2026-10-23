"""Testes automáticos da API. Rode com:  pytest"""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

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
