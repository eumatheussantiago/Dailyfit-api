// Funções compartilhadas pelas telas de cadastro, login e painel

const CHAVE_USUARIO = "dailyfit_usuario";

// Chama a API e devolve o JSON. Em caso de erro, lança uma mensagem amigável.
// Se o usuário estiver logado, envia o token de acesso junto.
async function api(caminho, { method = "GET", body } = {}) {
    const opcoes = { method, headers: {} };
    const token = obterUsuario()?.token;

    if (token) {
        opcoes.headers["Authorization"] = `Bearer ${token}`;
    }

    if (body !== undefined) {
        opcoes.headers["Content-Type"] = "application/json";
        opcoes.body = JSON.stringify(body);
    }

    let resposta;
    try {
        resposta = await fetch(caminho, opcoes);
    } catch {
        throw new Error("Não foi possível conectar ao servidor.");
    }

    if (resposta.status === 204) return null;

    const dados = await resposta.json().catch(() => null);

    // Token vencido ou inválido (ex.: login antigo, de antes desta versão): pede login de novo
    if (resposta.status === 401 && token) {
        sair();
        throw new Error("Sua sessão expirou. Faça login novamente.");
    }

    if (!resposta.ok) {
        throw new Error(mensagemDeErro(dados));
    }

    return dados;
}

// O FastAPI devolve erros de validação como lista; transforma em texto simples
function mensagemDeErro(dados) {
    if (!dados || !dados.detail) return "Algo deu errado. Tente novamente.";
    if (typeof dados.detail === "string") return dados.detail;

    const primeiro = dados.detail[0];
    const campo = primeiro?.loc?.[primeiro.loc.length - 1];
    const nomes = { nome: "Nome", email: "E-mail", senha: "Senha", descricao: "Descrição", idade: "Idade", altura: "Altura", peso_atual: "Peso atual", peso_meta: "Peso desejado" };
    const texto = (primeiro?.msg || "Dados inválidos").replace("Value error, ", "");

    if (texto.startsWith("String should have at least")) {
        return `${nomes[campo] || "Campo"} muito curto.`;
    }
    return nomes[campo] ? `${nomes[campo]}: ${texto}` : texto;
}

// lembrar = true  -> continua logado mesmo fechando o navegador (localStorage)
// lembrar = false -> sai ao fechar o navegador (sessionStorage)
// sem "lembrar": mantém onde o login já estava guardado
function salvarUsuario(usuario, lembrar) {
    try {
        if (lembrar === undefined) {
            lembrar = !sessionStorage.getItem(CHAVE_USUARIO);
        }
        localStorage.removeItem(CHAVE_USUARIO);
        sessionStorage.removeItem(CHAVE_USUARIO);
        const destino = lembrar ? localStorage : sessionStorage;
        destino.setItem(CHAVE_USUARIO, JSON.stringify(usuario));
    } catch {
        /* navegador sem armazenamento: segue sem lembrar o login */
    }
    window.__usuario = usuario;
}

// Só conta como logado quem tem token (logins de versões antigas não têm)
function obterUsuario() {
    let usuario = window.__usuario || null;
    try {
        const salvo =
            localStorage.getItem(CHAVE_USUARIO) ||
            sessionStorage.getItem(CHAVE_USUARIO);
        if (salvo) usuario = JSON.parse(salvo);
    } catch {
        /* ignora */
    }
    return usuario && usuario.token ? usuario : null;
}

function sair() {
    try {
        localStorage.removeItem(CHAVE_USUARIO);
        sessionStorage.removeItem(CHAVE_USUARIO);
    } catch {
        /* ignora */
    }
    window.location.href = "/login";
}

// Depois de entrar: quem ainda não respondeu o formulário inicial vai para ele
function destinoAposEntrar(usuario) {
    return usuario && usuario.perfil_preenchido ? "/painel" : "/formulario";
}

function redirecionarSeLogado() {
    const usuario = obterUsuario();
    if (usuario) window.location.href = destinoAposEntrar(usuario);
}

// Mensagem de status nas telas do grupo (usa o <p class="login-message">)
function mostrarMensagem(elemento, texto, tipo = "erro") {
    elemento.textContent = texto;
    elemento.style.color =
        tipo === "erro" ? "var(--laranja-principal)" : "var(--verde-escuro)";
}

function mostrarErro(id, mensagem) {
    const el = document.getElementById(id);
    el.textContent = mensagem;
    el.hidden = false;
}

function esconderErro(id) {
    document.getElementById(id).hidden = true;
}

let temporizadorToast;
function avisar(mensagem) {
    const toast = document.getElementById("toast");
    if (!toast) return;
    toast.textContent = mensagem;
    toast.classList.add("visivel");
    clearTimeout(temporizadorToast);
    temporizadorToast = setTimeout(() => toast.classList.remove("visivel"), 2500);
}

// Telas depois do login (base_logado.html): sem login volta para /login;
// com login mostra "Olá, Nome" e liga o botão Sair. Devolve o usuário logado.
function exigirLogin() {
    const usuario = obterUsuario();
    if (!usuario) {
        window.location.href = "/login";
        return null;
    }
    document.getElementById("ola").textContent = `Olá, ${usuario.nome?.split(" ")[0] || ""}`;
    document.getElementById("sair").addEventListener("click", sair);
    return usuario;
}

// Tipos de refeição: atalhos da tela Refeições, plano do Painel e ícones.
// Uma refeição é de um tipo quando o nome contém a chave (sem acento e sem maiúscula).
const TIPOS_REFEICAO = [
    { nome: "Café da manhã", icone: "☕", chave: "cafe", campo: "horario_cafe" },
    { nome: "Almoço", icone: "🥗", chave: "almoco", campo: "horario_almoco" },
    { nome: "Lanche", icone: "🍎", chave: "lanche" },
    { nome: "Jantar", icone: "🌙", chave: "jant", campo: "horario_jantar" },
];

const simplificar = (texto) => texto.normalize("NFD").replace(/\p{M}/gu, "").toLowerCase();
// Vale a chave que aparece primeiro no nome: "Lanche com café" é lanche, não café da manhã
function tipoDaRefeicao(nome) {
    const texto = simplificar(nome);
    let escolhido;
    let posicao = Infinity;
    for (const tipo of TIPOS_REFEICAO) {
        const i = texto.indexOf(tipo.chave);
        if (i >= 0 && i < posicao) {
            escolhido = tipo;
            posicao = i;
        }
    }
    return escolhido;
}

const plural = (n, um, varios) => `${n} ${n === 1 ? um : varios}`;

const formatarHora = new Intl.DateTimeFormat("pt-BR", { hour: "2-digit", minute: "2-digit" });

// Dias contados no horário do navegador (a API devolve as datas em UTC)
function meiaNoite(data) {
    const d = new Date(data);
    d.setHours(0, 0, 0, 0);
    return d;
}

// Anda os dias a partir do meio-dia: onde o horário de verão começa à meia-noite (ex.: o Brasil
// até 2019), aquela meia-noite não existe e partir dela erraria a chave dos outros dias
function diasAtras(n) {
    const d = new Date();
    d.setHours(12, 0, 0, 0);
    d.setDate(d.getDate() - n);
    return meiaNoite(d);
}

const chaveDia = (data) => meiaNoite(data).getTime();

// Refeições por dia (chave = meia-noite local): { total, dentro da dieta }
function refeicoesPorDia(refeicoes) {
    const dias = new Map();
    for (const r of refeicoes) {
        const chave = chaveDia(r.data_hora);
        const dia = dias.get(chave) || { total: 0, dentro: 0 };
        dia.total++;
        if (!r.nao_dieta) dia.dentro++;
        dias.set(chave, dia);
    }
    return dias;
}

// Dias seguidos com pelo menos uma refeição. Hoje ainda sem registro não quebra a sequência.
function diasSeguidos(dias) {
    let n = dias.has(chaveDia(new Date())) ? 0 : 1;
    let total = 0;
    while (dias.has(chaveDia(diasAtras(n)))) {
        total++;
        n++;
    }
    return total;
}

const OBJETIVOS = {
    emagrecimento: "Emagrecimento",
    ganho_massa: "Ganho de massa muscular",
    manutencao: "Manutenção do peso",
    reeducacao: "Reeducação alimentar",
};

// Rotina dos últimos 7 dias: refeições feitas ÷ planejadas (meta por dia). Conta só os dias
// desde a primeira refeição (quem começou ontem não fica com a semana "vazia") e um dia com
// refeição a mais não compensa outro.
function rotinaDaSemana(refeicoes, porDia, meta) {
    const inicio = meiaNoite(refeicoes.length ? refeicoes.at(-1).data_hora : new Date());
    let feitas = 0;
    let dias = 0;
    for (let n = 0; n < 7; n++) {
        const data = diasAtras(n);
        if (data < inicio) continue;
        dias++;
        feitas += Math.min(porDia.get(data.getTime())?.total || 0, meta);
    }
    return Math.round((feitas / (meta * Math.max(dias, 1))) * 100);
}

// Item de lista de uma refeição: ícone, nome, hora, descrição e selo dentro/fora da dieta
function criarItemRefeicao(refeicao) {
    const item = document.createElement("li");
    item.className = "refeicao-item";

    const icone = document.createElement("div");
    icone.className = "meal-icon";
    icone.setAttribute("aria-hidden", "true");
    icone.textContent = tipoDaRefeicao(refeicao.nome)?.icone || "🍽️";

    const info = document.createElement("div");
    info.className = "refeicao-info";

    const nome = document.createElement("strong");
    nome.textContent = refeicao.nome;

    const hora = document.createElement("small");
    hora.textContent = formatarHora.format(new Date(refeicao.data_hora));

    info.append(nome, hora);

    if (refeicao.descricao) {
        const desc = document.createElement("p");
        desc.textContent = refeicao.descricao;
        info.append(desc);
    }

    const selo = document.createElement("span");
    selo.className = refeicao.nao_dieta ? "selo selo-fora" : "selo selo-dentro";
    selo.textContent = refeicao.nao_dieta ? "Fora da dieta" : "Na dieta";

    item.append(icone, info, selo);
    return item;
}
