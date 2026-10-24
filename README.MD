# DailyFit

O **DailyFit** é uma plataforma web para organizar a alimentação e a rotina. O usuário cria uma conta, responde um formulário sobre seus objetivos, registra as refeições do dia, marca se estão dentro ou fora da dieta e acompanha o próprio progresso.

Projeto em grupo do curso de **Análise e Desenvolvimento de Sistemas (ADS)**.

## 🔗 Acesse online

**https://dailyfit-037t.onrender.com**

- Documentação da API: https://dailyfit-037t.onrender.com/docs
- O site usa o plano grátis do Render: depois de **15 minutos sem acesso ele "dorme"** e leva de **20 segundos a 1 minuto para abrir** de novo. Antes de apresentar, abra o link alguns minutos antes.

## Funcionalidades

- Página inicial de apresentação
- Cadastro com senha criptografada (a senha nunca é salva como texto)
- Login com e-mail e senha, com "Manter conectado" e botão "Mostrar senha"
- Cada usuário só acessa os próprios dados (token de acesso) e o login bloqueia após 10 senhas erradas
- Formulário inicial em 3 etapas (objetivo, medidas, alimentação e rotina), salvo no banco
- Painel com resumo da dieta e cadastro, edição e exclusão de refeições *(provisório — será substituído pelo dashboard do grupo)*
- Resumo: total de refeições, dentro e fora da dieta e melhor sequência
- API REST documentada automaticamente em `/docs`
- Testes automáticos com `pytest`

## Fluxo do usuário

```
Início → Criar conta → Formulário inicial (3 etapas) → Painel
Início → Entrar → Painel  (ou Formulário, se ainda não respondeu)
```

## Tecnologias

| Parte | Tecnologia |
|---|---|
| Back-end / API | Python, FastAPI |
| Banco de dados | SQLAlchemy — SQLite no computador, PostgreSQL (Supabase) no site publicado |
| Front-end | HTML, CSS, JavaScript |
| Hospedagem | Render |
| Testes | pytest |

## Estrutura do projeto

```
main.py          → inicia a aplicação e registra as rotas
database.py      → conexão com o banco de dados
seguranca.py     → criptografia das senhas, tokens de acesso e limite de tentativas
models/          → tabelas do banco (usuários, perfis e refeições)
schemas/         → formato e validação dos dados da API
routes/          → rotas da API e das páginas
templates/       → páginas HTML (início, cadastro, login, formulário e, depois do login, painel, refeições, objetivos e progresso)
static/css/      → estilos (style.css do grupo + app.css das telas depois do login)
static/js/       → scripts das páginas e da ligação com a API
tests/           → testes automáticos
render.yaml      → configuração do deploy no Render
iniciar.bat      → abre o app com dois cliques no Windows
```

## Como rodar no computador

### Jeito mais fácil (Windows)

Dê **dois cliques no arquivo `iniciar.bat`**. Ele instala tudo na primeira vez e abre o app no navegador.

Só precisa ter o [Python](https://www.python.org/downloads/) instalado. Na instalação, marque a opção **"Add python.exe to PATH"**.

Para desligar, feche a janela preta chamada **"DailyFit"**.

### Pelo terminal

Requisito: **Python 3.10 ou mais novo**.

```bash
# 1. criar um ambiente virtual (recomendado)
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

No computador, o banco é um arquivo `dailyfit.db` criado automaticamente na primeira execução. Ele **não** vai para o GitHub e é separado do banco do site publicado.

### Rodar os testes

```bash
pytest
```

Resultado esperado: `33 passed`.

## Deploy (site publicado)

| Parte | Serviço | Detalhes |
|---|---|---|
| Servidor | **Render** (plano grátis) | Região Ohio, configurado pelo `render.yaml` |
| Banco de dados | **Supabase** (plano grátis) | PostgreSQL, região `us-east-2` |

**Para atualizar o site, basta dar `git push` na branch `master`.** O Render publica a versão nova sozinho em 2 a 3 minutos.

### Dicas com IA (Claude Haiku 5.5)

A tela **Objetivos** tem o botão **"Gerar dicas"**: a IA escreve de 3 a 5 dicas para a semana a partir do formulário, dos números (IMC etc.) e das refeições dos últimos 7 dias.

- **Para ligar:** crie uma chave em [console.anthropic.com](https://console.anthropic.com), coloque um pouco de crédito e, no painel do Render, em **Environment**, crie `ANTHROPIC_API_KEY` com a chave. Sem a chave, as dicas ficam desligadas e o resto do site funciona normal. **Nunca coloque a chave no código.**
- **Custo:** cada geração custa menos de US$ 0,001. Cada pessoa gera no máximo uma vez a cada 20 horas, e o site todo no máximo `DICAS_LIMITE_DIA` vezes por dia (padrão 200). Vale definir também um limite de gasto no console da Anthropic.
- **Privacidade (LGPD):** para a IA vão só as respostas do formulário, os números e o resumo das refeições, **nunca nome nem e-mail**. Para gerar, a pessoa marca que concorda (a data do aceite fica salva) e precisa ter 18 anos ou mais.

### Variáveis de ambiente

Ficam **somente** no painel do Render (**Environment**), nunca no código:

| Variável | Para que serve |
|---|---|
| `DATABASE_URL` | Endereço do banco no Supabase. Contém a senha do banco: **não compartilhe** |
| `SECRET_KEY` | Chave que assina os tokens de login. Opcional: sem ela, a chave é derivada da `DATABASE_URL` |

Formato usado (Session pooler do Supabase):

```
postgresql://dailyfit_app.<id-do-projeto>:<senha>@aws-0-us-east-2.pooler.supabase.com:5432/postgres
```

### Segurança do banco

- O app usa um usuário próprio no banco (`dailyfit_app`), sem permissão de administrador.
- As tabelas têm **RLS** ligado: a API pública do Supabase não consegue ler os dados, só o app.
- As senhas dos usuários são salvas criptografadas (PBKDF2-SHA256).
- As rotas com `/usuarios/{id}` exigem o token do próprio usuário: ninguém lê nem altera dados de outra pessoa.
- Depois de 10 senhas erradas, o login daquele e-mail fica bloqueado por 15 minutos.

### Se o deploy falhar

| Erro nos logs do Render | O que fazer |
|---|---|
| `tenant/user ... not found` | O endereço do pooler está errado. Confira no Supabase em **Connect → Session pooler** e corrija a `DATABASE_URL` |
| `password authentication failed` | A senha na `DATABASE_URL` está errada |
| `No open ports detected` | O app não conseguiu iniciar. Veja o erro que aparece logo acima nos logs |

## Rotas da API

O cadastro e o login devolvem um **`token`**. As demais rotas exigem esse token no cabeçalho `Authorization: Bearer <token>` e só funcionam para o próprio usuário (🔒). No `/docs`, clique em **"Authorize"** e cole o token para testar.

| Método | Rota | O que faz |
|---|---|---|
| POST | `/usuarios` | Cria um usuário (devolve o token e o código de recuperação, só desta vez) |
| POST | `/usuarios/login` | Entra com e-mail e senha (devolve o token) |
| GET | `/usuarios/{id}` 🔒 | Mostra o próprio usuário |
| DELETE | `/usuarios/{id}` 🔒 | Apaga a conta e todos os dados (perfil, refeições, dicas) — botão em Objetivos |
| PUT | `/usuarios/{id}/perfil` 🔒 | Salva as respostas do formulário inicial |
| GET | `/usuarios/{id}/perfil` 🔒 | Mostra as respostas do formulário inicial |
| POST | `/usuarios/{id}/refeicoes` 🔒 | Cadastra uma refeição |
| GET | `/usuarios/{id}/refeicoes` 🔒 | Lista as refeições |
| GET | `/usuarios/{id}/refeicoes/{refeicao_id}` 🔒 | Mostra uma refeição |
| PUT | `/usuarios/{id}/refeicoes/{refeicao_id}` 🔒 | Edita uma refeição |
| DELETE | `/usuarios/{id}/refeicoes/{refeicao_id}` 🔒 | Exclui uma refeição |
| GET | `/usuarios/{id}/resumo` 🔒 | Métricas da dieta |
| GET | `/privacidade` | Política de privacidade (LGPD) |
| POST | `/usuarios/recuperar-senha` | Troca a senha com e-mail + código de recuperação (mesma trava de tentativas do login; devolve um código novo) |
| POST | `/usuarios/{id}/codigo-recuperacao` 🔒 | Gera um código de recuperação novo (o anterior deixa de valer) |
| GET | `/usuarios/{id}/dicas` 🔒 | Últimas dicas da IA e quando dá para gerar de novo |
| POST | `/usuarios/{id}/dicas` 🔒 | Gera dicas com IA (pede `{"consentimento": true}`, 18+ anos, 1 vez a cada 20 h) |

## Regras do grupo

- **Tela de início:** `templates/index.html`, `static/css/style.css` e `static/js/script.js` não devem ser alterados.
- **Telas de cadastro, login e formulário:** vêm do repositório do grupo [ME-Bastos/DailyFit](https://github.com/ME-Bastos/DailyFit). Mudanças de visual devem ser feitas lá e copiadas para cá.
- **Cores:** use apenas as variáveis do `:root`:

| Variável | Valor |
|---|---|
| `--laranja-principal` | `#ff8400f8` |
| `--verde-escuro` | `#287d45` |
| `--verde-claro` | `#60d050` |
| `--amarelo` | `#fdc500` |
| `--amarelo-hover` | `#f3c82f` |
| `--fundo` | `#f5f8f3` |
| `--fundo-verde` | `#edf7ef` |
| `--branco` | `#ffffff` |
| `--texto` | `#26352b` |
| `--texto-secundario` | `#657168` |
| `--borda` | `#e1e9e3` |
| `--sombra` | `0 20px 60px rgba(40, 125, 69, 0.10)` |
| `--radius` | `18px` |

### Telas depois do login

| Tela | Arquivos | O que faz |
|---|---|---|
| Painel (`/painel`) | `painel.html` + `painel.js` | Cartão "Hoje" da tela de início com os dados reais: % do dia, plano com os horários do formulário, dias seguidos, últimos 7 dias e objetivo |
| Refeições (`/refeicoes`) | `refeicoes.html` + `refeicoes.js` | Atalhos (café, almoço, lanche, jantar), adicionar, editar e excluir + histórico por dia |
| Objetivos (`/objetivos`) | `objetivos.html` + `objetivos.js` | Objetivo e meta de peso, metas da rotina, plano e respostas do formulário (`/treinos` leva para cá) |
| Progresso (`/progresso`) | `progresso.html` + `progresso.js` | Últimos 7 dias × 7 anteriores, dias seguidos, gráfico de 14 dias e total |

- As 4 telas usam o molde `templates/base_logado.html` (menu com as abas, "Olá" e botão Sair).
- Os dados vêm da API **pela função `api()` do `static/js/app.js`**, que já envia o token de acesso. O usuário logado vem de `exigirLogin()` (sem login, volta para `/login`). Não use campo de "ID do usuário": a API só mostra os dados do dono do token.
- Depois de mudar, rode `pytest`, teste com o `iniciar.bat` e dê `git push`.

## Próximos passos

- Recuperação de senha: feita com **código de recuperação** (aparece uma vez depois do cadastro; em Objetivos dá para gerar outro). Se um dia o site mandar e-mail, dá para trocar por link no e-mail.
- Hábitos e metas personalizadas
