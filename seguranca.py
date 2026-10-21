"""Segurança: senhas criptografadas, tokens de acesso e limite de tentativas de login.

- A senha nunca é guardada como texto: o banco recebe só um "hash"
  (PBKDF2-SHA256 com sal aleatório), que não pode ser revertido.
- Depois do cadastro/login, o usuário recebe um token assinado. Toda rota
  com /usuarios/{id} exige esse token e só aceita o dono dos dados.
"""

import base64
import hashlib
import hmac
import json
import os
import secrets
import threading
import time
from collections import defaultdict, deque

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from database import DATABASE_URL

# ---------------------------------------------------------------- senhas

ALGORITMO = "pbkdf2_sha256"
ITERACOES = 390_000


def gerar_hash_senha(senha: str) -> str:
    sal = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", senha.encode(), sal.encode(), ITERACOES)
    return f"{ALGORITMO}${ITERACOES}${sal}${digest.hex()}"


def verificar_senha(senha: str, hash_salvo: str | None) -> bool:
    if not hash_salvo:
        return False
    try:
        algoritmo, iteracoes, sal, digest_salvo = hash_salvo.split("$")
    except ValueError:
        return False
    if algoritmo != ALGORITMO:
        return False
    digest = hashlib.pbkdf2_hmac("sha256", senha.encode(), sal.encode(), int(iteracoes))
    return hmac.compare_digest(digest.hex(), digest_salvo)


# Usado quando o e-mail não existe: gasta o mesmo tempo de uma senha real,
# para que o tempo de resposta não revele quais e-mails estão cadastrados.
HASH_FALSO = gerar_hash_senha(secrets.token_hex(16))


# ---------------------------------------------------------------- tokens

# Chave que assina os tokens. Em produção, defina SECRET_KEY no Render.
# Sem ela, a chave é derivada do endereço do banco (que já é secreto),
# então os tokens continuam válidos depois que o servidor reinicia.
_CHAVE = (
    os.getenv("SECRET_KEY")
    or hashlib.sha256(f"dailyfit-token:{DATABASE_URL}".encode()).hexdigest()
).encode()

VALIDADE_TOKEN = 60 * 60 * 24 * 30  # 30 dias


def _b64(dados: bytes) -> str:
    return base64.urlsafe_b64encode(dados).rstrip(b"=").decode()


def _de_b64(texto: str) -> bytes:
    return base64.urlsafe_b64decode(texto + "=" * (-len(texto) % 4))


def _assinar(conteudo: str) -> str:
    return _b64(hmac.new(_CHAVE, conteudo.encode(), hashlib.sha256).digest())


def gerar_token(usuario_id: int) -> str:
    conteudo = _b64(json.dumps({"sub": usuario_id, "exp": int(time.time()) + VALIDADE_TOKEN}).encode())
    return f"{conteudo}.{_assinar(conteudo)}"


def ler_token(token: str) -> int | None:
    """Devolve o id do usuário se o token for válido e não tiver expirado."""
    try:
        conteudo, assinatura = token.split(".")
        if not hmac.compare_digest(assinatura, _assinar(conteudo)):
            return None
        dados = json.loads(_de_b64(conteudo))
        if dados["exp"] < time.time():
            return None
        return int(dados["sub"])
    except (ValueError, KeyError, TypeError):
        return None


_bearer = HTTPBearer(auto_error=False, description="Token recebido no cadastro ou no login")


def exigir_dono(
    usuario_id: int,
    credenciais: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> int:
    """Libera a rota só para o próprio usuário (o dono do {usuario_id})."""
    if credenciais is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Faça login para continuar",
            headers={"WWW-Authenticate": "Bearer"},
        )

    dono = ler_token(credenciais.credentials)
    if dono is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sua sessão expirou. Faça login novamente",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if dono != usuario_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem acesso aos dados de outro usuário",
        )

    return dono


# ---------------------------------------------------------------- limite de tentativas

MAX_TENTATIVAS = 10
JANELA_SEGUNDOS = 15 * 60

_tentativas: dict[str, deque] = defaultdict(deque)
_trava = threading.Lock()


def checar_limite_login(email: str) -> None:
    """Bloqueia o e-mail por um tempo depois de muitas senhas erradas seguidas."""
    agora = time.monotonic()
    with _trava:
        fila = _tentativas[email]
        while fila and agora - fila[0] > JANELA_SEGUNDOS:
            fila.popleft()
        if len(fila) >= MAX_TENTATIVAS:
            espera = int(JANELA_SEGUNDOS - (agora - fila[0])) // 60 + 1
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Muitas tentativas. Tente de novo em {espera} min",
            )


def registrar_falha_login(email: str) -> None:
    agora = time.monotonic()
    with _trava:
        _tentativas[email].append(agora)

        # Evita que a memória cresça sem limite se alguém testar muitos e-mails
        if len(_tentativas) > 5000:
            for chave in [c for c, fila in _tentativas.items() if agora - fila[-1] > JANELA_SEGUNDOS]:
                del _tentativas[chave]


def limpar_falhas_login(email: str) -> None:
    with _trava:
        _tentativas.pop(email, None)
