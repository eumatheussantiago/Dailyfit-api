from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

import models  # registra as tabelas antes de criá-las
from database import Base, engine
from routes.pagina import router as pagina_router
from routes.refeicoes import router as refeicoes_router
from routes.resumo import router as resumo_router
from routes.usuarios import router as usuarios_router

BASE_DIR = Path(__file__).resolve().parent

# Cria as tabelas do banco (se ainda não existirem)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="DailyFit API",
    description="API para controle de usuários e refeições",
    version="1.0.0",
)

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

app.include_router(pagina_router)
app.include_router(usuarios_router)
app.include_router(refeicoes_router)
app.include_router(resumo_router)
