"""Criptografia de senhas.

A senha nunca é guardada como texto: o banco recebe só um "hash"
(PBKDF2-SHA256 com sal aleatório), que não pode ser revertido.
"""

import hashlib
import hmac
import secrets

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
