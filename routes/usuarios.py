from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models.usuario import UsuarioModel
from schemas.usuario import (
    CodigoRecuperacao,
    RecuperarSenha,
    UsuarioCreate,
    UsuarioLogado,
    UsuarioLogin,
    UsuarioResponse,
)
from seguranca import (
    HASH_FALSO,
    checar_limite_login,
    codigo_confere,
    exigir_dono,
    gerar_codigo_recuperacao,
    gerar_hash_senha,
    gerar_token,
    hash_do_codigo,
    limpar_falhas_login,
    registrar_falha_login,
    verificar_senha,
)


router = APIRouter(
    prefix="/usuarios",
    tags=["Usuários"]
)


def com_token(usuario: UsuarioModel, codigo_recuperacao: str | None = None) -> UsuarioLogado:
    dados = UsuarioResponse.model_validate(usuario).model_dump()
    return UsuarioLogado(**dados, token=gerar_token(usuario.id), codigo_recuperacao=codigo_recuperacao)


def novo_codigo(usuario: UsuarioModel) -> str:
    """Gera um código de recuperação novo; o anterior deixa de valer."""
    codigo = gerar_codigo_recuperacao()
    usuario.codigo_recuperacao_hash = hash_do_codigo(codigo)
    return codigo


# CRIAR USUÁRIO
@router.post(
    "",
    response_model=UsuarioLogado,
    status_code=status.HTTP_201_CREATED
)
def criar_usuario(
    usuario: UsuarioCreate,
    db: Session = Depends(get_db)
):
    usuario_existente = (
        db.query(UsuarioModel.id)
        .filter(UsuarioModel.email == usuario.email)
        .first()
    )

    if usuario_existente:
        raise HTTPException(
            status_code=400,
            detail="Email já cadastrado"
        )

    novo_usuario = UsuarioModel(
        nome=usuario.nome,
        email=usuario.email,
        senha_hash=gerar_hash_senha(usuario.senha)
    )
    codigo = novo_codigo(novo_usuario)

    db.add(novo_usuario)
    db.commit()
    db.refresh(novo_usuario)

    return com_token(novo_usuario, codigo)


# ENTRAR (confere e-mail e senha)
@router.post(
    "/login",
    response_model=UsuarioLogado
)
def entrar(
    dados: UsuarioLogin,
    db: Session = Depends(get_db)
):
    checar_limite_login(dados.email)

    usuario = (
        db.query(UsuarioModel)
        .filter(UsuarioModel.email == dados.email)
        .first()
    )

    # Confere a senha mesmo quando o e-mail não existe (com um hash falso),
    # para que o tempo de resposta seja igual nos dois casos.
    senha_ok = verificar_senha(dados.senha, usuario.senha_hash if usuario else HASH_FALSO)

    # Mesma mensagem para e-mail ou senha errados: não revela quais e-mails existem
    if not usuario or not senha_ok:
        registrar_falha_login(dados.email)
        raise HTTPException(
            status_code=401,
            detail="E-mail ou senha incorretos"
        )

    limpar_falhas_login(dados.email)
    return com_token(usuario)


# RECUPERAR SENHA com o código de recuperação (o site não manda e-mail)
@router.post("/recuperar-senha", response_model=UsuarioLogado)
def recuperar_senha(
    dados: RecuperarSenha,
    db: Session = Depends(get_db)
):
    # Mesma trava de tentativas do login: ninguém testa códigos sem parar
    checar_limite_login(dados.email)

    usuario = (
        db.query(UsuarioModel)
        .filter(UsuarioModel.email == dados.email)
        .first()
    )
    codigo_ok = codigo_confere(dados.codigo, usuario.codigo_recuperacao_hash if usuario else None)

    # Mesma mensagem para e-mail ou código errados: não revela quais e-mails existem
    if not codigo_ok:
        registrar_falha_login(dados.email)
        raise HTTPException(
            status_code=400,
            detail="E-mail ou código de recuperação incorretos"
        )

    limpar_falhas_login(dados.email)
    usuario.senha_hash = gerar_hash_senha(dados.nova_senha)
    codigo = novo_codigo(usuario)  # cada código vale uma vez só
    db.commit()
    db.refresh(usuario)

    return com_token(usuario, codigo)


# GERAR UM CÓDIGO DE RECUPERAÇÃO NOVO (precisa do token; o anterior deixa de valer)
@router.post(
    "/{usuario_id}/codigo-recuperacao",
    response_model=CodigoRecuperacao,
    dependencies=[Depends(exigir_dono)]
)
def gerar_novo_codigo(
    usuario_id: int,
    db: Session = Depends(get_db)
):
    usuario = db.get(UsuarioModel, usuario_id)

    if not usuario:
        raise HTTPException(
            status_code=404,
            detail="Usuário não encontrado"
        )

    codigo = novo_codigo(usuario)
    db.commit()

    return CodigoRecuperacao(codigo_recuperacao=codigo)


# OBTER O PRÓPRIO USUÁRIO (precisa do token)
@router.get(
    "/{usuario_id}",
    response_model=UsuarioResponse,
    dependencies=[Depends(exigir_dono)]
)
def obter_usuario(
    usuario_id: int,
    db: Session = Depends(get_db)
):
    usuario = db.get(UsuarioModel, usuario_id)

    if not usuario:
        raise HTTPException(
            status_code=404,
            detail="Usuário não encontrado"
        )

    return usuario
