from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

import models  # registra as tabelas antes de criá-las
from database import criar_tabelas
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

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

app.include_router(pagina_router)
app.include_router(usuarios_router)
app.include_router(perfil_router)
app.include_router(refeicoes_router)
app.include_router(resumo_router)
