import json
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

import ia
from database import agora_utc, get_db
from models.dica import DicaModel
from models.perfil import PerfilModel
from models.refeicao import RefeicaoModel
from models.usuario import UsuarioModel
from saude import calcular_indicadores
from seguranca import exigir_dono


router = APIRouter(
    prefix="/usuarios/{usuario_id}/dicas",
    tags=["Dicas com IA"],
    dependencies=[Depends(exigir_dono)]  # só o dono dos dados acessa
)

# "Uma vez por dia" sem obrigar a pessoa a esperar o mesmo horário de ontem
INTERVALO_ENTRE_GERACOES = timedelta(hours=20)

# Só o que a IA precisa saber do formulário (nada de nome, e-mail ou id)
CAMPOS_DO_FORMULARIO = [
    "objetivo", "sexo", "idade", "altura", "peso_atual", "peso_meta", "atividade",
    "tipo_alimentacao", "restricoes", "preferencias", "refeicoes_por_dia",
    "horario_cafe", "horario_almoco", "horario_jantar", "dificuldades_rotina",
]


class DicasResponse(BaseModel):
    ligadas: bool                    # False quando o site não tem a chave da IA
    dicas: list[ia.Dica]
    criado_em: Optional[datetime]
    proxima_em: Optional[datetime]   # a partir de quando dá para gerar de novo


def limite_do_site() -> int:
    """Gerações permitidas no site todo em 24 h (protege a conta de surpresas)."""
    return int(os.getenv("DICAS_LIMITE_DIA", "200"))


def buscar_usuario(usuario_id: int, db: Session) -> UsuarioModel:
    usuario = db.get(UsuarioModel, usuario_id)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return usuario


def ultima_dica(usuario_id: int, db: Session) -> Optional[DicaModel]:
    return (
        db.query(DicaModel)
        .filter(DicaModel.usuario_id == usuario_id)
        .order_by(DicaModel.criado_em.desc(), DicaModel.id.desc())
        .first()
    )


def montar_resposta(dica: Optional[DicaModel]) -> DicasResponse:
    if not dica:
        return DicasResponse(ligadas=ia.dicas_ligadas(), dicas=[], criado_em=None, proxima_em=None)
    # O banco guarda em UTC sem fuso; devolve com fuso para o navegador converter
    criado_em = dica.criado_em.replace(tzinfo=timezone.utc)
    return DicasResponse(
        ligadas=ia.dicas_ligadas(),
        dicas=json.loads(dica.conteudo),
        criado_em=criado_em,
        proxima_em=criado_em + INTERVALO_ENTRE_GERACOES,
    )


def montar_dados(perfil: PerfilModel, refeicoes: list[RefeicaoModel]) -> dict:
    """O que vai para a IA: formulário, números calculados e resumo dos últimos 7 dias."""
    formulario = {campo: getattr(perfil, campo) for campo in CAMPOS_DO_FORMULARIO}
    fora_da_dieta = sum(1 for refeicao in refeicoes if refeicao.nao_dieta)
    return {
        "formulario": formulario,
        "numeros": calcular_indicadores(
            sexo=perfil.sexo,
            idade=perfil.idade,
            altura=perfil.altura,
            peso_atual=perfil.peso_atual,
            peso_meta=perfil.peso_meta,
            atividade=perfil.atividade,
        ),
        "ultimos_7_dias": {
            "refeicoes_registradas": len(refeicoes),
            "dentro_da_dieta": len(refeicoes) - fora_da_dieta,
            "fora_da_dieta": fora_da_dieta,
            # aproximado: dias contados em UTC (o servidor não sabe o fuso da pessoa)
            "dias_com_registro": len({refeicao.data_hora.date() for refeicao in refeicoes}),
            "refeicoes": [
                {"nome": refeicao.nome, "fora_da_dieta": refeicao.nao_dieta}
                for refeicao in refeicoes[:40]
            ],
        },
    }


# ÚLTIMAS DICAS GERADAS
@router.get("", response_model=DicasResponse)
def obter_dicas(usuario_id: int, db: Session = Depends(get_db)):
    buscar_usuario(usuario_id, db)
    return montar_resposta(ultima_dica(usuario_id, db))


# GERAR DICAS NOVAS (chama a IA)
@router.post("", response_model=DicasResponse)
def gerar_dicas(usuario_id: int, db: Session = Depends(get_db)):
    usuario = buscar_usuario(usuario_id, db)

    if not ia.dicas_ligadas():
        raise HTTPException(status_code=503, detail="As dicas com IA ainda não foram ligadas neste site.")
    if not usuario.perfil:
        raise HTTPException(status_code=400, detail="Responda o formulário inicial antes de gerar dicas.")

    agora = agora_utc()
    ultima = ultima_dica(usuario_id, db)
    if ultima and agora - ultima.criado_em < INTERVALO_ENTRE_GERACOES:
        raise HTTPException(status_code=429, detail="Você já gerou suas dicas hoje. Volte amanhã para novas dicas.")

    geradas_no_dia = (
        db.query(func.count(DicaModel.id))
        .filter(DicaModel.criado_em >= agora - timedelta(days=1))
        .scalar()
    )
    if geradas_no_dia >= limite_do_site():
        raise HTTPException(status_code=503, detail="O limite de dicas do site por hoje acabou. Tente de novo amanhã.")

    refeicoes = (
        db.query(RefeicaoModel)
        .filter(RefeicaoModel.usuario_id == usuario_id, RefeicaoModel.data_hora >= agora - timedelta(days=7))
        .order_by(RefeicaoModel.data_hora.desc())
        .all()
    )

    try:
        dicas = ia.gerar_dicas(montar_dados(usuario.perfil, refeicoes))
    except ia.ErroDicas as erro:
        raise HTTPException(status_code=503, detail=str(erro)) from erro

    nova = DicaModel(usuario_id=usuario_id, conteudo=json.dumps(dicas, ensure_ascii=False))
    db.add(nova)
    db.commit()
    db.refresh(nova)

    return montar_resposta(nova)
