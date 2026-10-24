from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
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
    MAX_CADASTROS_POR_IP,
    checar_limite_login,
    codigo_confere,
    exigir_dono,
    gerar_codigo_recuperacao,
    gerar_hash_senha,
    gerar_token,
    hash_do_codigo,
    ip_do_cliente,
    limpar_falhas_login,
    registrar_falha_login,
    travas,
    verificar_senha,
)


router = APIRouter(
    prefix="/usuarios",
    tags=["Usuários"]
)


def com_token(usuario: UsuarioModel, codigo_recuperacao: str | None = None) -> UsuarioLogado:
    dados = UsuarioResponse.model_validate(usuario).model_dump()
    return UsuarioLogado(**dados, token=gerar_token(usuario.id, usuario.senha_hash), codigo_recuperacao=codigo_recuperacao)


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
    request: Request,
    db: Session = Depends(get_db)
):
    # Conta toda tentativa de cadastro do IP (não só as que dão certo)
    chave_ip = f"cad:{ip_do_cliente(request)}"
    checar_limite_login(chave_ip, MAX_CADASTROS_POR_IP)
    registrar_falha_login(chave_ip)

    # O hash é lento (~0,6 s; vários segundos no Render grátis): calcula antes de usar o banco,
    # para não segurar uma das poucas conexões enquanto isso
    senha_hash = gerar_hash_senha(usuario.senha)

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
        senha_hash=senha_hash
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
    request: Request,
    db: Session = Depends(get_db)
):
    contadores = travas("login", dados.email, ip_do_cliente(request))
    for chave, maximo in contadores:
        checar_limite_login(chave, maximo)

    usuario = (
        db.query(UsuarioModel)
        .filter(UsuarioModel.email == dados.email)
        .first()
    )
    hash_salvo = usuario.senha_hash if usuario else HASH_FALSO
    db.rollback()  # só leitura: devolve a conexão ao pool antes do hash lento

    # Confere a senha mesmo quando o e-mail não existe (com um hash falso),
    # para que o tempo de resposta seja igual nos dois casos.
    senha_ok = verificar_senha(dados.senha, hash_salvo)

    # Mesma mensagem para e-mail ou senha errados: não revela quais e-mails existem
    if not usuario or not senha_ok:
        for chave, _ in contadores:
            registrar_falha_login(chave)
        raise HTTPException(
            status_code=401,
            detail="E-mail ou senha incorretos"
        )

    limpar_falhas_login(contadores[0][0])  # só o contador deste IP
    return com_token(usuario)  # recarrega o usuário do banco (rápido)


# RECUPERAR SENHA com o código de recuperação (o site não manda e-mail)
@router.post("/recuperar-senha", response_model=UsuarioLogado)
def recuperar_senha(
    dados: RecuperarSenha,
    request: Request,
    db: Session = Depends(get_db)
):
    # Trava parecida com a do login, mas com contador próprio: ninguém testa códigos sem parar
    contadores = travas("rec", dados.email, ip_do_cliente(request))
    for chave, maximo in contadores:
        checar_limite_login(chave, maximo)

    usuario = (
        db.query(UsuarioModel)
        .filter(UsuarioModel.email == dados.email)
        .first()
    )
    hash_codigo = usuario.codigo_recuperacao_hash if usuario else None
    codigo_ok = codigo_confere(dados.codigo, hash_codigo)

    # Mesma mensagem para e-mail ou código errados: não revela quais e-mails existem
    erro = HTTPException(
        status_code=400,
        detail="E-mail ou código de recuperação incorretos"
    )
    if not codigo_ok:
        for chave, _ in contadores:
            registrar_falha_login(chave)
        raise erro

    limpar_falhas_login(contadores[0][0])
    db.rollback()  # devolve a conexão ao pool antes do hash lento da senha nova
    nova_senha_hash = gerar_hash_senha(dados.nova_senha)

    # Recarrega do banco: se o mesmo código foi usado por outro pedido nesse meio-tempo, recusa
    if usuario.codigo_recuperacao_hash != hash_codigo:
        raise erro
    usuario.senha_hash = nova_senha_hash
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


# APAGAR A PRÓPRIA CONTA (LGPD, art. 18): perfil, refeições e dicas vão junto
@router.delete(
    "/{usuario_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(exigir_dono)]
)
def apagar_usuario(
    usuario_id: int,
    db: Session = Depends(get_db)
):
    usuario = db.get(UsuarioModel, usuario_id)

    if not usuario:
        raise HTTPException(
            status_code=404,
            detail="Usuário não encontrado"
        )

    db.delete(usuario)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
