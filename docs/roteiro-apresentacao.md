# Roteiro da apresentação do DailyFit

Tempo sugerido: **8 a 10 minutos**. Site: https://dailyfit-037t.onrender.com

## Na véspera e no dia

- **Não mexa no código no dia:** nenhum merge nem push na `master` desde a véspera. Cada publicação reinicia o site, e ele fica uns 5 minutos fora do ar (erro 503) enquanto a versão nova sobe. Quem abrir nessa hora acha que o site "dormiu".
- **Mantenha a sequência de dias:** registre pelo menos uma refeição por dia na conta que vai ser mostrada, ou complete os dias vazios na véspera (passo 2 abaixo). Um dia sem refeição zera o "Dias seguidos" no Painel e no Progresso.
- **Dicas com IA:** cada conta gera dicas uma vez a cada 20 horas. Se as dicas da conta já foram geradas há menos de 20 horas, mostre as que estão na tela em vez de gerar ao vivo (o botão mostra quando libera de novo).

## Antes de começar (no dia, 10 minutos antes)

1. **Abra o site:** o plano grátis do Render dorme depois de 15 minutos sem visitas, mas o UptimeRobot visita a cada 5 minutos e o mantém acordado (99,98% no ar em 30 dias). Abra o link mesmo assim para conferir. Se demorar, aparece o aviso "O servidor está acordando…": espere até 1 minuto.
2. **Conta de demonstração com dados:** no computador do grupo, rode o comando abaixo uma vez. A senha é digitada na hora.
   ```
   python scripts/criar_conta_demo.py https://dailyfit-037t.onrender.com demo@dailyfit.app
   ```
   Ele cria a conta "Maria Demonstração" com o formulário respondido e uma semana de refeições com horário.
   **Também serve para completar uma conta de verdade** (troque o e-mail pelo seu): mantém o formulário que já está respondido e só cria refeições nos dias dos últimos 7 que estiverem vazios. Não apaga nem troca nada.
   O dono do projeto tem também um SQL que faz o mesmo direto no Supabase (pede a ele).
3. Deixe **duas abas** abertas: a tela de início e o login já feito com a conta de demonstração.
4. As dicas com IA estão ligadas (a chave `ANTHROPIC_API_KEY` está no Render). Se um dia a chave sair, a seção mostra "ainda não foram ligadas", e o resto funciona normal.

## A apresentação

| # | Tela | O que mostrar | O que falar |
|---|---|---|---|
| 1 | **Início** (`/`) | Cartão "Hoje" com 75%, refeições com horário, "7 dias de sequência" | "Esta é a promessa do app: acompanhar o dia, as refeições e o progresso." |
| 2 | **Criar conta** | Criar uma conta ao vivo. Depois aparece o **código de recuperação** | "Sem e-mail, a recuperação de senha usa este código, que aparece uma vez só." |
| 3 | **Formulário inicial** | As 3 etapas: objetivo, alimentação, rotina. Use idade 18+, altura em centímetros (ex.: 175) e meta que combine com o objetivo | "Com essas respostas o app personaliza tudo. Ele recusa dados que não fazem sentido, como meta maior que o peso para quem quer emagrecer." |
| 4 | **Painel** (conta demo) | % do dia, plano com café, almoço e jantar nos horários do formulário, dias seguidos, gráfico da semana | "É o cartão da tela de início com os dados reais da pessoa." |
| 5 | **Refeições** | Atalhos ☕🥗🍎🌙, campo **"Quando?"**, histórico por dia, editar e excluir | "Dá para lançar uma refeição esquecida, e a sequência de dias não quebra." |
| 6 | **Objetivos** | "Seu corpo em números": IMC (OMS), peso saudável, gasto calórico, água, prazo até a meta | "Calculado no servidor com fórmulas conhecidas (OMS, Mifflin-St Jeor), com aviso de que não substitui profissional." |
| 7 | **Objetivos → Dicas com IA** | Marcar o consentimento → "Gerar dicas" → 3 a 5 dicas | "Claude Haiku 5.5: menos de US$ 0,001 por geração. Não vai nome nem e-mail para a IA (LGPD), uma geração a cada 20 horas por pessoa." |
| 8 | **Progresso** | 7 dias × 7 anteriores, recordes, gráfico de 14 dias | "Na dieta embaixo, fora da dieta em cima. Cores testadas para daltonismo." |
| 9 | **Celular** | Abrir o site no celular | "Tudo funciona em tela pequena." |

## Se perguntarem

- **Tecnologias:** Python (FastAPI e SQLAlchemy), PostgreSQL (Supabase), HTML, CSS e JavaScript sem framework, Render, IA Claude (Anthropic).
- **Segurança:** senha com hash (PBKDF2), login por token, cada pessoa só acessa os próprios dados, trava depois de 10 senhas erradas, senha pedida de novo para gerar código de recuperação ou apagar a conta, RLS no banco.
- **Testes:** `pytest` com 46 testes automáticos, que rodam sem gastar com a IA.
- **O site fica no ar como?** Plano grátis do Render, mantido acordado pelo UptimeRobot (checa a cada 5 minutos e avisa se cair).
- **Acessibilidade:** contraste conferido texto a texto, foco do teclado visível, leitor de tela.

## Recado para o grupo (repositório ME-Bastos/DailyFit)

**Termos de uso e política de privacidade:** agora existem em `/termos` e `/privacidade`. No cadastro (`templates/cadastro.html`), o texto "Aceito os termos de uso e a política de privacidade." pode virar dois links: `<a href="/termos">termos de uso</a>` e `<a href="/privacidade">política de privacidade</a>`. Vale também colocar os dois links no rodapé da tela de início. Esses arquivos são do grupo, por isso não mexemos neles.


Nas telas depois do login, o texto laranja foi escurecido para passar no contraste mínimo de leitura (4,5:1). Para isso foi criada a variável `--laranja-texto` no `app.css`, misturando o `--laranja-principal` com o `--texto`. **Na tela de início, no cadastro e no login, que são do grupo, o laranja continua como está**, e alguns textos ficam abaixo do mínimo:

- texto laranja sobre fundo claro (`.section-label`, títulos com `<span>` laranja, links "Entrar"): **cerca de 2,3:1 a 2,4:1**;
- texto branco sobre botão laranja: **2,5:1**;
- "Fit" amarelo sobre a barra laranja, no logo: pode ficar como está, porque logotipos não entram na regra.

Sugestão para o `style.css`: criar `--laranja-texto` (um laranja mais escuro, por exemplo uma mistura de 55% do laranja com 45% do `--texto`) para textos laranja, e usar texto escuro (`--texto`) nos botões laranja, como já está nas telas logadas.
