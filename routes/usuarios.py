from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models.usuario import UsuarioModel
from schemas.usuario import UsuarioCreate, UsuarioLogin, UsuarioResponse
from seguranca import gerar_hash_senha, verificar_senha


router = APIRouter(
    prefix="/usuarios",
    tags=["Usuários"]
)


# CRIAR USUÁRIO
@router.post(
    "",
    response_model=UsuarioResponse,
    status_code=status.HTTP_201_CREATED
)
def criar_usuario(
    usuario: UsuarioCreate,
    db: Session = Depends(get_db)
):
    usuario_existente = (
        db.query(UsuarioModel)
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

    return novo_usuario


# ENTRAR (confere e-mail e senha)
@router.post(
    "/login",
    response_model=UsuarioResponse
)
def entrar(
    dados: UsuarioLogin,
    db: Session = Depends(get_db)
):
    usuario = (
        db.query(UsuarioModel)
        .filter(UsuarioModel.email == dados.email)
        .first()
    )

    # Mesma mensagem para e-mail ou senha errados: não revela quais e-mails existem
    if not usuario or not verificar_senha(dados.senha, usuario.senha_hash):
        raise HTTPException(
            status_code=401,
            detail="E-mail ou senha incorretos"
        )

    return usuario


# LISTAR USUÁRIOS
@router.get(
    "",
    response_model=list[UsuarioResponse]
)
def listar_usuarios(
    db: Session = Depends(get_db)
):
    return db.query(UsuarioModel).all()


# OBTER UM USUÁRIO
@router.get(
    "/{usuario_id}",
    response_model=UsuarioResponse
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
