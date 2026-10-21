from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models.refeicao import RefeicaoModel
from models.usuario import UsuarioModel
from seguranca import exigir_dono


router = APIRouter(
    prefix="/usuarios/{usuario_id}",
    tags=["Resumo"],
    dependencies=[Depends(exigir_dono)]  # só o dono dos dados acessa
)


@router.get("/resumo")
def obter_resumo(
    usuario_id: int,
    db: Session = Depends(get_db)
):
    if not db.get(UsuarioModel, usuario_id):
        raise HTTPException(
            status_code=404,
            detail="Usuário não encontrado"
        )

    # Busca só a coluna necessária (dentro/fora da dieta), em ordem cronológica,
    # em vez de carregar todas as refeições inteiras.
    fora_da_dieta = (
        db.query(RefeicaoModel.nao_dieta)
        .filter(RefeicaoModel.usuario_id == usuario_id)
        .order_by(RefeicaoModel.data_hora.asc(), RefeicaoModel.id.asc())
        .all()
    )

    total_refeicoes = len(fora_da_dieta)
    dentro_dieta = 0
    melhor_sequencia = 0
    sequencia_atual = 0

    # Uma única passada: conta as refeições na dieta e a maior sequência seguida
    for (nao_dieta,) in fora_da_dieta:
        if nao_dieta:
            sequencia_atual = 0
        else:
            dentro_dieta += 1
            sequencia_atual += 1
            melhor_sequencia = max(melhor_sequencia, sequencia_atual)

    return {
        "total_refeicoes_cadastradas": total_refeicoes,
        "total_refeicoes_dentro_da_dieta": dentro_dieta,
        "total_refeicoes_fora_da_dieta": total_refeicoes - dentro_dieta,
        "melhor_sequencia_de_refeicoes_dentro_da_dieta": melhor_sequencia
    }
