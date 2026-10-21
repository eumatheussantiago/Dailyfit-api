from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models.usuario import UsuarioModel
from schemas.usuario import UsuarioCreate, UsuarioLogin, UsuarioLogado, UsuarioResponse
from seguranca import (
    HASH_FALSO,
    checar_limite_login,
    exigir_dono,
    gerar_hash_senha,
    gerar_token,
    limpar_falhas_login,
    registrar_falha_login,
    verificar_senha,
)


router = APIRouter(
    prefix="/usuarios",
    tags=["Usuários"]
)


def com_token(usuario: UsuarioModel) -> UsuarioLogado:
    dados = UsuarioResponse.model_validate(usuario).model_dump()
    return UsuarioLogado(**dados, token=gerar_token(usuario.id))


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

    db.add(novo_usuario)
    db.commit()
    db.refresh(novo_usuario)

    return com_token(novo_usuario)


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
