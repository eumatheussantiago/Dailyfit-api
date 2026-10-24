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

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from database import DATABASE_URL, USANDO_SQLITE, get_db
from models.usuario import UsuarioModel

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

# Código de recuperação de senha (o site não manda e-mail): 12 caracteres sem os que se confundem
# (0/O, 1/I/L), mostrado uma única vez e guardado só como hash. Por ser aleatório (~59 bits) e
# ter a trava de tentativas do login, basta SHA-256: o PBKDF2 lento é para senha escolhida por
# gente, e no Render grátis deixaria o cadastro vários segundos mais lento.
ALFABETO_CODIGO = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


def gerar_codigo_recuperacao() -> str:
    letras = "".join(secrets.choice(ALFABETO_CODIGO) for _ in range(12))
    return "-".join(letras[i:i + 4] for i in range(0, 12, 4))  # ex.: "K7PQ-ZM3T-RW9H"


def normalizar_codigo(codigo: str) -> str:
    """Aceita com ou sem traços e em minúsculas."""
    return "".join(letra for letra in codigo.upper() if letra.isalnum())


def hash_do_codigo(codigo: str) -> str:
    return hashlib.sha256(normalizar_codigo(codigo).encode()).hexdigest()


def codigo_confere(codigo: str, hash_salvo: str | None) -> bool:
    normalizado = normalizar_codigo(codigo)
    # compare_digest: o tempo da comparação não revela quantos caracteres batem
    return bool(normalizado and hash_salvo) and hmac.compare_digest(hash_do_codigo(normalizado), hash_salvo)


# ---------------------------------------------------------------- tokens

# Chave que assina os tokens. Em produção (PostgreSQL) a SECRET_KEY do Render é obrigatória:
# sem ela o app nem inicia. No SQLite local, a chave é derivada do caminho do banco.
_segredo = os.getenv("SECRET_KEY")
if not _segredo and not USANDO_SQLITE:
    raise RuntimeError("Defina SECRET_KEY")
_CHAVE = (_segredo or hashlib.sha256(f"dailyfit-token:{DATABASE_URL}".encode()).hexdigest()).encode()

VALIDADE_TOKEN = 60 * 60 * 24 * 30  # 30 dias


def _b64(dados: bytes) -> str:
    return base64.urlsafe_b64encode(dados).rstrip(b"=").decode()


def _de_b64(texto: str) -> bytes:
    return base64.urlsafe_b64decode(texto + "=" * (-len(texto) % 4))


def _assinar(conteudo: str) -> str:
    return _b64(hmac.new(_CHAVE, conteudo.encode(), hashlib.sha256).digest())


def carimbo_da_senha(senha_hash: str | None) -> str:
    """Pedacinho derivado da senha atual: trocar a senha invalida os tokens antigos."""
    return hashlib.sha256((senha_hash or "").encode()).hexdigest()[:16]


def gerar_token(usuario_id: int, senha_hash: str | None) -> str:
    dados = {"sub": usuario_id, "exp": int(time.time()) + VALIDADE_TOKEN, "sv": carimbo_da_senha(senha_hash)}
    conteudo = _b64(json.dumps(dados).encode())
    return f"{conteudo}.{_assinar(conteudo)}"


def ler_token(token: str) -> tuple[int, str] | None:
    """Devolve (id do usuário, carimbo da senha) se o token for válido e não tiver expirado."""
    try:
        conteudo, assinatura = token.split(".")
        if not hmac.compare_digest(assinatura, _assinar(conteudo)):
            return None
        dados = json.loads(_de_b64(conteudo))
        if dados["exp"] < time.time():
            return None
        return int(dados["sub"]), str(dados["sv"])
    except (ValueError, KeyError, TypeError):
        return None


_bearer = HTTPBearer(auto_error=False, description="Token recebido no cadastro ou no login")


def exigir_dono(
    usuario_id: int,
    credenciais: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> int:
    """Libera a rota só para o próprio usuário (o dono do {usuario_id})."""
    if credenciais is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Faça login para continuar",
            headers={"WWW-Authenticate": "Bearer"},
        )

    sessao_expirada = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Sua sessão expirou. Faça login novamente.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    lido = ler_token(credenciais.credentials)
    if lido is None:
        raise sessao_expirada
    dono, carimbo = lido

    # Conta apagada ou senha trocada depois do login: o token antigo não vale mais
    usuario = db.query(UsuarioModel.senha_hash).filter(UsuarioModel.id == dono).first()
    if usuario is None or not hmac.compare_digest(carimbo, carimbo_da_senha(usuario.senha_hash)):
        raise sessao_expirada

    if dono != usuario_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem acesso aos dados de outro usuário",
        )

    return dono


# ---------------------------------------------------------------- limite de tentativas

# shortcut: trava em memória, zera no reinício; migrar para tabela se o app crescer
MAX_TENTATIVAS = 10        # por e-mail + IP: quem erra é bloqueado, a dona da conta (outro IP) não
MAX_POR_EMAIL = 50         # por e-mail sozinho: segura força bruta espalhada em muitos IPs
MAX_CADASTROS_POR_IP = 30  # alto de propósito: a turma toda pode estar no mesmo Wi-Fi
JANELA_SEGUNDOS = 15 * 60

_tentativas: dict[str, deque] = defaultdict(deque)
_trava = threading.Lock()


def ip_do_cliente(request: Request) -> str:
    """IP de quem fez o pedido. No Render, o proxy ACRESCENTA o IP real no fim do
    X-Forwarded-For; o começo da lista vem do cliente e pode ser inventado."""
    encaminhado = request.headers.get("x-forwarded-for")
    if encaminhado:
        return encaminhado.split(",")[-1].strip()
    return request.client.host if request.client else "desconhecido"


def travas(prefixo: str, email: str, ip: str) -> list[tuple[str, int]]:
    """Contadores (chave, máximo) de uma ação: "login" e "rec" (recuperação) contam separado."""
    return [(f"{prefixo}:{email}:{ip}", MAX_TENTATIVAS), (f"{prefixo}:{email}", MAX_POR_EMAIL)]


def checar_limite_login(chave: str, maximo: int = MAX_TENTATIVAS) -> None:
    """Bloqueia a chave por um tempo depois de muitas tentativas na janela."""
    agora = time.monotonic()
    with _trava:
        fila = _tentativas[chave]
        while fila and agora - fila[0] > JANELA_SEGUNDOS:
            fila.popleft()
        if len(fila) >= maximo:
            espera = int(JANELA_SEGUNDOS - (agora - fila[0])) // 60 + 1
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Muitas tentativas. Tente de novo em {espera} min",
            )


def registrar_falha_login(chave: str) -> None:
    agora = time.monotonic()
    with _trava:
        _tentativas[chave].append(agora)

        # Evita que a memória cresça sem limite se alguém testar muitos e-mails
        if len(_tentativas) > 5000:
            for velha in [c for c, fila in _tentativas.items() if not fila or agora - fila[-1] > JANELA_SEGUNDOS]:
                del _tentativas[velha]


def limpar_falhas_login(chave: str) -> None:
    with _trava:
        _tentativas.pop(chave, None)
