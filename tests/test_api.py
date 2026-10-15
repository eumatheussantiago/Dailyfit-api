"""Testes automáticos da API. Rode com:  pytest"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

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
    yield TestClient(app)
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine_teste)


def criar_usuario(client, email="ana@email.com"):
    resposta = client.post("/usuarios", json={"nome": "Ana", "email": email, "senha": "segredo123"})
    assert resposta.status_code == 201
    return resposta.json()["id"]


def test_paginas_abrem(client):
    for pagina in ["/", "/cadastro", "/login", "/formulario", "/painel"]:
        assert client.get(pagina).status_code == 200
    assert client.get("/static/css/style.css").status_code == 200
    assert client.get("/static/js/script.js").status_code == 200


def test_cadastro_e_login(client):
    usuario_id = criar_usuario(client, "Ana@Email.com ")

    duplicado = client.post("/usuarios", json={"nome": "Ana", "email": "ana@email.com", "senha": "outra123"})
    assert duplicado.status_code == 400

    login = client.post("/usuarios/login", json={"email": "ANA@email.com", "senha": "segredo123"})
    assert login.status_code == 200
    assert login.json()["id"] == usuario_id
    assert login.json()["perfil_preenchido"] is False

    senha_errada = client.post("/usuarios/login", json={"email": "ana@email.com", "senha": "errada123"})
    assert senha_errada.status_code == 401
    assert client.post("/usuarios/login", json={"email": "x@y.com", "senha": "segredo123"}).status_code == 401


def test_senha_nao_fica_salva_em_texto(client):
    from models.usuario import UsuarioModel

    criar_usuario(client)
    resposta = client.get("/usuarios").json()[0]
    assert "senha" not in resposta and "senha_hash" not in resposta

    with SessaoTeste() as db:
        hash_salvo = db.query(UsuarioModel).first().senha_hash
    assert "segredo123" not in hash_salvo
    assert hash_salvo.startswith("pbkdf2_sha256$")


def test_validacoes(client):
    assert client.post("/usuarios", json={"nome": "A", "email": "a@b.com", "senha": "segredo123"}).status_code == 422
    assert client.post("/usuarios", json={"nome": "Ana", "email": "invalido", "senha": "segredo123"}).status_code == 422
    assert client.post("/usuarios", json={"nome": "Ana", "email": "a@b.com", "senha": "123"}).status_code == 422

    usuario_id = criar_usuario(client)
    vazio = client.post(f"/usuarios/{usuario_id}/refeicoes", json={"nome": "   "})
    assert vazio.status_code == 422


def test_crud_de_refeicoes(client):
    usuario_id = criar_usuario(client)
    base = f"/usuarios/{usuario_id}/refeicoes"

    criada = client.post(base, json={"nome": "Almoço", "descricao": "Arroz e feijão", "nao_dieta": False})
    assert criada.status_code == 201
    refeicao_id = criada.json()["id"]

    assert client.get(f"{base}/{refeicao_id}").json()["nome"] == "Almoço"

    editada = client.put(f"{base}/{refeicao_id}", json={"nome": "Almoço leve", "nao_dieta": True})
    assert editada.status_code == 200
    assert editada.json()["nao_dieta"] is True

    assert client.delete(f"{base}/{refeicao_id}").status_code == 204
    assert client.get(f"{base}/{refeicao_id}").status_code == 404


def test_refeicao_de_outro_usuario_nao_aparece(client):
    ana = criar_usuario(client, "ana@email.com")
    bia = criar_usuario(client, "bia@email.com")

    refeicao = client.post(f"/usuarios/{ana}/refeicoes", json={"nome": "Café", "nao_dieta": False}).json()

    assert client.get(f"/usuarios/{bia}/refeicoes/{refeicao['id']}").status_code == 404
    assert client.delete(f"/usuarios/{bia}/refeicoes/{refeicao['id']}").status_code == 404


def test_resumo(client):
    usuario_id = criar_usuario(client)
    base = f"/usuarios/{usuario_id}/refeicoes"

    for nome, fora in [("Café", False), ("Lanche", False), ("Pizza", True), ("Almoço", False), ("Jantar", False), ("Ceia", False)]:
        client.post(base, json={"nome": nome, "nao_dieta": fora})

    resumo = client.get(f"/usuarios/{usuario_id}/resumo").json()
    assert resumo == {
        "total_refeicoes_cadastradas": 6,
        "total_refeicoes_dentro_da_dieta": 5,
        "total_refeicoes_fora_da_dieta": 1,
        "melhor_sequencia_de_refeicoes_dentro_da_dieta": 3,
    }

    assert client.get("/usuarios/999/resumo").status_code == 404


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
    usuario_id = criar_usuario(client)
    url = f"/usuarios/{usuario_id}/perfil"

    assert client.get(url).status_code == 404

    salvo = client.put(url, json=PERFIL)
    assert salvo.status_code == 200
    assert salvo.json()["preferencias"] is None  # texto vazio vira vazio no banco

    # Responder de novo atualiza em vez de duplicar
    atualizado = client.put(url, json={**PERFIL, "peso_atual": 69})
    assert atualizado.json()["peso_atual"] == 69
    assert client.get(url).json()["peso_atual"] == 69

    login = client.post("/usuarios/login", json={"email": "ana@email.com", "senha": "segredo123"})
    assert login.json()["perfil_preenchido"] is True

    assert client.put(url, json={**PERFIL, "objetivo": "voar"}).status_code == 422
    assert client.put(url, json={**PERFIL, "horario_cafe": "25:00"}).status_code == 422
    assert client.put("/usuarios/999/perfil", json=PERFIL).status_code == 404


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
    finally:
        database.engine.dispose()
        database.engine = engine_original
