"""Testes das correções da auditoria de segurança. Rode com:  pytest"""

import os
import subprocess
import sys
from pathlib import Path

from starlette.requests import Request

import routes.usuarios
import seguranca
from database import get_db
from main import app
from models.refeicao import RefeicaoModel
from tests.test_api import SessaoTeste, client, criar_usuario  # noqa: F401 (client é fixture)

ERRADO = {"email": "ana@email.com", "senha": "errada123"}
CERTO = {"email": "ana@email.com", "senha": "segredo123"}


def ip(endereco):
    return {"X-Forwarded-For": endereco}


def test_trocar_senha_derruba_sessoes_antigas(client):
    cadastro = client.post("/usuarios", json={"nome": "Ana", "email": "ana@email.com", "senha": "segredo123"}).json()
    antigo = {"Authorization": f"Bearer {cadastro['token']}"}
    assert client.get(f"/usuarios/{cadastro['id']}", headers=antigo).status_code == 200

    nova = client.post("/usuarios/recuperar-senha", json={
        "email": "ana@email.com", "codigo": cadastro["codigo_recuperacao"], "nova_senha": "nova12345"}).json()

    recusado = client.get(f"/usuarios/{cadastro['id']}", headers=antigo)
    assert recusado.status_code == 401 and recusado.json()["detail"] == "Sua sessão expirou. Faça login novamente."
    assert client.get(f"/usuarios/{cadastro['id']}", headers={"Authorization": f"Bearer {nova['token']}"}).status_code == 200


def test_ip_do_cliente_usa_o_ultimo_item_do_proxy():
    def pedido(cabecalhos):
        return Request({"type": "http", "headers": cabecalhos, "client": ("10.0.0.1", 1234)})

    assert seguranca.ip_do_cliente(pedido([])) == "10.0.0.1"
    # o cliente inventou "6.6.6.6"; o proxy do Render acrescentou o IP real no fim
    assert seguranca.ip_do_cliente(pedido([(b"x-forwarded-for", b"6.6.6.6, 1.2.3.4")])) == "1.2.3.4"


def test_atacante_nao_trava_a_dona_da_conta(client):
    criar_usuario(client)
    for _ in range(seguranca.MAX_TENTATIVAS):
        assert client.post("/usuarios/login", json=ERRADO, headers=ip("6.6.6.6")).status_code == 401

    # o atacante fica bloqueado, mesmo forjando outro IP no começo do cabeçalho
    assert client.post("/usuarios/login", json=CERTO, headers=ip("6.6.6.6")).status_code == 429
    assert client.post("/usuarios/login", json=CERTO, headers=ip("1.1.1.1, 6.6.6.6")).status_code == 429
    # a recuperação tem contador próprio: não foi bloqueada pelos erros de login
    rec = {"email": "ana@email.com", "codigo": "AAAA-AAAA-AAAA", "nova_senha": "nova12345"}
    assert client.post("/usuarios/recuperar-senha", json=rec, headers=ip("6.6.6.6")).status_code == 400
    # a dona, de outro IP, entra normalmente
    assert client.post("/usuarios/login", json=CERTO, headers=ip("2.2.2.2")).status_code == 200


def test_teto_por_email_segura_ataque_de_varios_ips(client, monkeypatch):
    monkeypatch.setattr(seguranca, "MAX_POR_EMAIL", 3)
    criar_usuario(client)
    for numero in range(3):
        assert client.post("/usuarios/login", json=ERRADO, headers=ip(f"9.9.9.{numero}")).status_code == 401
    assert client.post("/usuarios/login", json=CERTO, headers=ip("9.9.9.200")).status_code == 429


def test_limite_de_cadastros_por_ip(client, monkeypatch):
    monkeypatch.setattr(routes.usuarios, "MAX_CADASTROS_POR_IP", 2)
    criar_usuario(client, "a@email.com")
    # e-mail repetido também conta como tentativa
    assert client.post("/usuarios", json={"nome": "Ana", "email": "a@email.com", "senha": "segredo123"}).status_code == 400
    bloqueado = client.post("/usuarios", json={"nome": "Bia", "email": "b@email.com", "senha": "segredo123"})
    assert bloqueado.status_code == 429 and "Muitas tentativas" in bloqueado.json()["detail"]


def test_hash_lento_nao_segura_a_conexao_do_banco(client, monkeypatch):
    sessoes = []

    def get_db_espiao():
        db = SessaoTeste()
        sessoes.append(db)
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = get_db_espiao
    original_hash, original_verificar = routes.usuarios.gerar_hash_senha, routes.usuarios.verificar_senha

    def sem_transacao_aberta(funcao):
        def espiao(*args):
            assert not sessoes[-1].in_transaction(), "hash rodando com a conexão do banco aberta"
            return funcao(*args)
        return espiao

    monkeypatch.setattr(routes.usuarios, "gerar_hash_senha", sem_transacao_aberta(original_hash))
    monkeypatch.setattr(routes.usuarios, "verificar_senha", sem_transacao_aberta(original_verificar))

    cadastro = client.post("/usuarios", json={"nome": "Ana", "email": "ana@email.com", "senha": "segredo123"})
    assert cadastro.status_code == 201
    assert client.post("/usuarios/login", json=CERTO).status_code == 200
    rec = {"email": "ana@email.com", "codigo": cadastro.json()["codigo_recuperacao"], "nova_senha": "nova12345"}
    assert client.post("/usuarios/recuperar-senha", json=rec).status_code == 200


def test_apagar_a_propria_conta(client):
    usuario_id, token = criar_usuario(client)
    client.post(f"/usuarios/{usuario_id}/refeicoes", json={"nome": "Café", "nao_dieta": False}, headers=token)
    _, token_bia = criar_usuario(client, "bia@email.com")

    assert client.delete(f"/usuarios/{usuario_id}").status_code == 401
    assert client.delete(f"/usuarios/{usuario_id}", headers=token_bia).status_code == 403
    assert client.delete(f"/usuarios/{usuario_id}", headers=token).status_code == 204

    assert client.get(f"/usuarios/{usuario_id}", headers=token).status_code == 401
    assert client.post("/usuarios/login", json=CERTO).status_code == 401
    with SessaoTeste() as db:
        assert db.query(RefeicaoModel).filter(RefeicaoModel.usuario_id == usuario_id).count() == 0


def test_cabecalhos_novos(client):
    pagina = client.get("/")
    assert "frame-ancestors 'none'" in pagina.headers["Content-Security-Policy"]
    assert pagina.headers["Strict-Transport-Security"] == "max-age=31536000; includeSubDomains"
    assert pagina.headers["Permissions-Policy"] == "camera=(), microphone=(), geolocation=()"
    # a documentação usa scripts de CDN: fica sem CSP
    assert "Content-Security-Policy" not in client.get("/docs").headers


def test_tamanho_maximo_no_login_e_recuperacao(client):
    assert client.post("/usuarios/login", json={"email": "a@b.com", "senha": "x" * 129}).status_code == 422
    assert client.post("/usuarios/login", json={"email": "a" * 250 + "@b.com", "senha": "x"}).status_code == 422
    rec = {"email": "a@b.com", "codigo": "AAAA", "nova_senha": "x" * 129}
    assert client.post("/usuarios/recuperar-senha", json=rec).status_code == 422


def test_secret_key_obrigatoria_em_producao():
    ambiente = {**os.environ, "DATABASE_URL": "postgresql://usuario@localhost/banco"}
    ambiente.pop("SECRET_KEY", None)
    resultado = subprocess.run(
        [sys.executable, "-c", "import seguranca"],
        cwd=Path(__file__).resolve().parent.parent, env=ambiente, capture_output=True, text=True,
    )
    assert resultado.returncode != 0 and "Defina SECRET_KEY" in resultado.stderr
