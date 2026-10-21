from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models.perfil import PerfilModel
from models.usuario import UsuarioModel
from schemas.perfil import PerfilResponse, PerfilSalvar
from seguranca import exigir_dono


router = APIRouter(
    prefix="/usuarios/{usuario_id}/perfil",
    tags=["Perfil (formulário inicial)"],
    dependencies=[Depends(exigir_dono)]  # só o dono dos dados acessa
)


def buscar_usuario(usuario_id: int, db: Session) -> UsuarioModel:
    usuario = db.get(UsuarioModel, usuario_id)

    if not usuario:
        raise HTTPException(
            status_code=404,
            detail="Usuário não encontrado"
        )

    return usuario


# SALVAR PERFIL (cria na primeira vez, atualiza nas próximas)
@router.put(
    "",
    response_model=PerfilResponse
)
def salvar_perfil(
    usuario_id: int,
    dados: PerfilSalvar,
    db: Session = Depends(get_db)
):
    usuario = buscar_usuario(usuario_id, db)

    perfil = usuario.perfil or PerfilModel(usuario_id=usuario_id)

    for campo, valor in dados.model_dump().items():
        setattr(perfil, campo, valor)

    db.add(perfil)
    db.commit()
    db.refresh(perfil)

    return perfil


# OBTER PERFIL
@router.get(
    "",
    response_model=PerfilResponse
)
def obter_perfil(
    usuario_id: int,
    db: Session = Depends(get_db)
):
    usuario = buscar_usuario(usuario_id, db)

    if not usuario.perfil:
        raise HTTPException(
            status_code=404,
            detail="Formulário inicial ainda não preenchido"
        )

    return usuario.perfil
