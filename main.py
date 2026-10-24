from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles

import models  # registra as tabelas antes de criá-las
from database import criar_tabelas
from routes.dicas import router as dicas_router
from routes.pagina import router as pagina_router
from routes.perfil import router as perfil_router
from routes.refeicoes import router as refeicoes_router
from routes.resumo import router as resumo_router
from routes.usuarios import router as usuarios_router

BASE_DIR = Path(__file__).resolve().parent

# Cria as tabelas do banco (e colunas novas, se o banco for de uma versão antiga)
criar_tabelas()

app = FastAPI(
    title="DailyFit API",
    description="API para controle de usuários, perfil e refeições",
    version="1.0.0",
)



# Só deixa o navegador carregar o que as páginas usam de verdade (bloqueia script injetado)
CSP = (
    "default-src 'self'; script-src 'self'; "
    "style-src 'self' https://fonts.googleapis.com https://cdn.jsdelivr.net; "
    "font-src https://fonts.gstatic.com; img-src 'self' data: https://images.unsplash.com; "
    "connect-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
)


@app.middleware("http")
async def cabecalhos_de_seguranca(request: Request, call_next):
    """Proteções básicas do navegador em todas as respostas."""
    resposta = await call_next(request)
    resposta.headers.setdefault("X-Content-Type-Options", "nosniff")
    resposta.headers.setdefault("X-Frame-Options", "DENY")
    resposta.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    resposta.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    resposta.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    # /docs e /redoc carregam scripts de CDN: ficam sem CSP
    if request.url.path not in ("/docs", "/redoc"):
        resposta.headers.setdefault("Content-Security-Policy", CSP)
    # Sem isto o navegador reusa JS/CSS antigos por horas depois de um deploy (o ETag deixa a conferência barata)
    resposta.headers.setdefault("Cache-Control", "no-cache")
    return resposta


app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

app.include_router(pagina_router)
app.include_router(usuarios_router)
app.include_router(perfil_router)
app.include_router(refeicoes_router)
app.include_router(resumo_router)
app.include_router(dicas_router)
