# DailyFit

O **DailyFit** é uma plataforma web para organizar a alimentação e a rotina. O usuário cria uma conta, registra as refeições do dia, marca se estão dentro ou fora da dieta e acompanha o próprio progresso.

Projeto desenvolvido para o curso de **Análise e Desenvolvimento de Sistemas (ADS)**.

## Funcionalidades

- Página inicial de apresentação
- Cadastro e login (pelo e-mail)
- Painel com resumo: total de refeições, dentro e fora da dieta, melhor sequência e porcentagem
- Cadastrar, editar e excluir refeições
- API REST documentada automaticamente em `/docs`
- Testes automáticos com `pytest`

## Tecnologias

| Parte | Tecnologia |
|---|---|
| Back-end / API | Python, FastAPI |
| Banco de dados | SQLite + SQLAlchemy |
| Front-end | HTML, CSS, JavaScript |
| Testes | pytest |

## Estrutura do projeto

```
main.py          → inicia a aplicação e registra as rotas
database.py      → conexão com o banco de dados (SQLite)
models/          → tabelas do banco (usuários e refeições)
schemas/         → formato e validação dos dados da API
routes/          → rotas da API e das páginas
templates/       → páginas HTML (início, cadastro, login, painel)
static/css/      → estilos
static/js/       → scripts das páginas
tests/           → testes automáticos
```

## Como rodar

Requisito: **Python 3.10 ou mais novo**.

```bash
# 1. (opcional, recomendado) criar um ambiente virtual
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# 2. instalar as dependências
pip install -r requirements.txt

# 3. iniciar o servidor
uvicorn main:app --reload
```

Depois abra no navegador:

- **App:** http://127.0.0.1:8000
- **Documentação da API:** http://127.0.0.1:8000/docs

O banco `dailyfit.db` é criado automaticamente na primeira execução.

## Rodar os testes

```bash
pytest
```

## Rotas da API

| Método | Rota | O que faz |
|---|---|---|
| POST | `/usuarios` | Cria um usuário |
| POST | `/usuarios/login` | Entra com o e-mail |
| GET | `/usuarios` | Lista usuários |
| GET | `/usuarios/{id}` | Mostra um usuário |
| POST | `/usuarios/{id}/refeicoes` | Cadastra uma refeição |
| GET | `/usuarios/{id}/refeicoes` | Lista as refeições |
| GET | `/usuarios/{id}/refeicoes/{refeicao_id}` | Mostra uma refeição |
| PUT | `/usuarios/{id}/refeicoes/{refeicao_id}` | Edita uma refeição |
| DELETE | `/usuarios/{id}/refeicoes/{refeicao_id}` | Exclui uma refeição |
| GET | `/usuarios/{id}/resumo` | Métricas da dieta |

## Próximos passos

- Login com senha (hash com `bcrypt`) e token JWT
- Gráfico de evolução semanal
- Hábitos e metas personalizadas
