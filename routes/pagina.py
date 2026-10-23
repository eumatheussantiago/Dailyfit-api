from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).resolve().parent.parent

router = APIRouter(include_in_schema=False)
templates = Jinja2Templates(directory=BASE_DIR / "templates")


def _pagina(nome: str):
    def view(request: Request):
        return templates.TemplateResponse(request=request, name=nome)
    return view


router.add_api_route("/", _pagina("index.html"), methods=["GET"])
router.add_api_route("/cadastro", _pagina("cadastro.html"), methods=["GET"])
router.add_api_route("/login", _pagina("login.html"), methods=["GET"])
router.add_api_route("/formulario", _pagina("formulario.html"), methods=["GET"])
router.add_api_route("/painel", _pagina("painel.html"), methods=["GET"])
router.add_api_route("/refeicoes", _pagina("refeicoes.html"), methods=["GET"])
router.add_api_route("/objetivos", _pagina("objetivos.html"), methods=["GET"])
# A tela Treinos virou Objetivos: o endereço antigo leva para ela (redirecionamento temporário,
# caso treinos volte a existir)
router.add_api_route("/treinos", lambda: RedirectResponse("/objetivos"), methods=["GET"])
router.add_api_route("/progresso", _pagina("progresso.html"), methods=["GET"])
