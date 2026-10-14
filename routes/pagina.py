from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

# Caminho absoluto: funciona mesmo que o servidor seja iniciado de outra pasta
BASE_DIR = Path(__file__).resolve().parent.parent

router = APIRouter()

templates = Jinja2Templates(directory=BASE_DIR / "templates")


@router.get("/")
def pagina_inicial(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html"
    )
