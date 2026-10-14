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
    resposta = client.post("/usuarios", json={"nome": "Ana", "email": email})
    assert resposta.status_code == 201
    return resposta.json()["id"]


def test_paginas_abrem(client):
    for pagina in ["/", "/cadastro", "/login", "/painel"]:
        assert client.get(pagina).status_code == 200
    assert client.get("/static/css/style.css").status_code == 200


def test_cadastro_e_login(client):
    usuario_id = criar_usuario(client, "Ana@Email.com ")

    duplicado = client.post("/usuarios", json={"nome": "Ana", "email": "ana@email.com"})
    assert duplicado.status_code == 400

    login = client.post("/usuarios/login", json={"email": "ANA@email.com"})
    assert login.status_code == 200
    assert login.json()["id"] == usuario_id

    assert client.post("/usuarios/login", json={"email": "x@y.com"}).status_code == 404


def test_validacoes(client):
    assert client.post("/usuarios", json={"nome": "A", "email": "a@b.com"}).status_code == 422
    assert client.post("/usuarios", json={"nome": "Ana", "email": "invalido"}).status_code == 422

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
