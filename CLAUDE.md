# DailyFit — contexto do projeto

Projeto em grupo da faculdade de ADS. App web de alimentação/rotina: o usuário cria conta,
responde um formulário inicial (3 etapas), registra refeições (dentro/fora da dieta) e vê um resumo.

- Repositório: github.com/eumatheussantiago/Dailyfit-api (branch principal: master)
- Telas originais do grupo: github.com/ME-Bastos/DailyFit
- Site publicado: https://dailyfit-037t.onrender.com  (API documentada em /docs)

## Stack
- Back-end: Python 3.12, FastAPI, SQLAlchemy 2, Jinja2 (templates), Uvicorn
- Banco: SQLite local (dailyfit.db, criado sozinho) | PostgreSQL no Supabase em produção (driver psycopg 3)
- Front-end: HTML + CSS + JavaScript puro (sem framework)
- Deploy: Render, plano grátis, configurado em render.yaml. Todo push na master publica sozinho (2-3 min)
- Testes: pytest (tests/test_api.py) — 15 testes, todos devem passar

## Estrutura
main.py        app FastAPI, middleware de cabeçalhos de segurança, cria tabelas ao iniciar
database.py    conexão; DATABASE_URL por variável de ambiente; criar_tabelas() adiciona colunas/índices
               novos em bancos existentes e liga RLS no Postgres; agora_utc() para datas
seguranca.py   hash de senha (PBKDF2-SHA256), tokens assinados (HMAC, 30 dias), exigir_dono(),
               limite de 10 senhas erradas por e-mail a cada 15 min
models/        usuarios, perfis (formulário inicial), refeicoes (índice usuario_id + data_hora)
schemas/       validação Pydantic
routes/        pagina.py (páginas), usuarios.py, perfil.py, refeicoes.py, resumo.py
templates/     index, cadastro, login, formulario (do grupo)
               base_app (cabeçalho, style.css + app.css e app.js) > base_logado (molde das telas
               depois do login: abas Painel/Refeições/Objetivos/Progresso, "Olá" e botão Sair)
               painel, refeicoes, objetivos, progresso (telas depois do login)
static/js/     app.js (função api() que envia o token, obterUsuario(), salvarUsuario(), sair(),
               exigirLogin(), buscarPerfil() (null só no 404), TIPOS_REFEICAO/tipoDaRefeicao()
               (café, almoço, lanche, jantar: nome sem acento contém a chave; vale a que aparece
               primeiro, "Café da tarde" é lanche), datas no fuso local (meiaNoite, diasAtras, chaveDia),
               refeicoesPorDia(), diasSeguidos(), plural(), criarItemRefeicao())
               cadastro.js, login.js, formulario.js, script.js (do grupo)
               painel.js (cartão "Hoje" da landing com dados reais: % do dia, plano pelos horários
               do formulário, dias seguidos, semana e objetivo), refeicoes.js (atalhos de nome, adicionar/
               editar/excluir, histórico por dia; /refeicoes?nome=X já preenche o nome),
               progresso.js (7 dias × 7 anteriores, dias seguidos, gráfico de 14 dias, total),
               objetivos.js (objetivo e meta de peso, metas da rotina, plano e respostas do formulário)
static/css/    style.css (do grupo) + app.css (só as 4 telas depois do login)
iniciar.bat    roda o app no Windows com dois cliques

## Autenticação
- POST /usuarios (cadastro) e POST /usuarios/login devolvem { id, nome, email, perfil_preenchido, token }
- Todas as rotas /usuarios/{id}/... exigem "Authorization: Bearer <token>" do PRÓPRIO usuário
  (401 sem login/token inválido, 403 para outro usuário). Não existe rota que liste usuários.
- No front, use sempre a função api() de static/js/app.js: ela já envia o token e, se der 401,
  manda de volta para o login.
- Telas depois do login: estenda templates/base_logado.html e comece o script com
  `const usuario = exigirLogin();` (sem login, volta para /login). Nunca peça "ID do usuário" na tela.
- Datas são salvas em UTC e devolvidas com "Z"; o navegador converte para o horário local.

## Regras do grupo (obrigatórias)
- NÃO alterar o visual de: templates/index.html, cadastro.html, login.html, formulario.html,
  static/css/style.css, static/js/script.js. Mudanças de visual são feitas no repositório
  ME-Bastos/DailyFit e copiadas para cá.
- Cores apenas pelas variáveis do :root do style.css (--laranja-principal, --verde-escuro,
  --verde-claro, --amarelo, --amarelo-hover, --fundo, --fundo-verde, --branco, --texto,
  --texto-secundario, --borda, --sombra, --radius). Nunca cor fixa (#hex/rgba) em arquivos novos.
- Nunca colocar senhas, DATABASE_URL ou SECRET_KEY no código/commits (ficam só no Render).
- Sempre trabalhar em branch separada e abrir pull request. Não fazer merge sem aprovação.
- Explicar tudo em português simples, como para um leigo.

## Como rodar e testar
pip install -r requirements.txt
uvicorn main:app --reload        -> http://127.0.0.1:8000
pytest                           -> esperado: 15 passed

## Estado atual (21/10/2026)
- Concluído e publicado: banco, cadastro/login com senha e token, formulário inicial, refeições,
  resumo, deploy no Render + Supabase, correções de segurança e de horário (PR #2), imagens da
  tela de início leves (~9,5 MB → 331 KB, PR #3) e as 4 telas depois do login no visual do site
  (Painel, Refeições, Treinos, Progresso, PR #4).
- Telas logadas sendo refeitas a partir da promessa da landing, uma por PR: Painel (cartão
  "Hoje"), Refeições (atalhos + histórico por dia) e Progresso (semana × semana anterior,
  gráfico de 14 dias) e Objetivos (no lugar de Treinos, decisão de 22/10/2026; /treinos
  redireciona para /objetivos) prontos.
  Dias e semana são contados no horário do navegador, a partir da lista de refeições.
  Para andar entre dias use diasAtras()/chaveDia() (partem do meio-dia; nunca setDate() direto
  numa meia-noite, que não existe onde o horário de verão começa à meia-noite).

## Pendências
1. Recuperação de senha ("Esqueci minha senha" hoje só mostra um aviso).
