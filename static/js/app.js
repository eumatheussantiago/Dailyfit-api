// Funções compartilhadas pelas telas de cadastro, login e painel

const CHAVE_USUARIO = "dailyfit_usuario";

// Chama a API e devolve o JSON. Em caso de erro, lança uma mensagem amigável.
async function api(caminho, { method = "GET", body } = {}) {
    const opcoes = { method, headers: {} };

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
    const nomes = { nome: "Nome", email: "E-mail", descricao: "Descrição" };
    const texto = (primeiro?.msg || "Dados inválidos").replace("Value error, ", "");

    if (texto.startsWith("String should have at least")) {
        return `${nomes[campo] || "Campo"} muito curto.`;
    }
    return nomes[campo] ? `${nomes[campo]}: ${texto}` : texto;
}

function salvarUsuario(usuario) {
    try {
        localStorage.setItem(CHAVE_USUARIO, JSON.stringify(usuario));
    } catch {
        /* navegador sem armazenamento: segue sem lembrar o login */
    }
    window.__usuario = usuario;
}

function obterUsuario() {
    try {
        const salvo = localStorage.getItem(CHAVE_USUARIO);
        if (salvo) return JSON.parse(salvo);
    } catch {
        /* ignora */
    }
    return window.__usuario || null;
}

function sair() {
    try {
        localStorage.removeItem(CHAVE_USUARIO);
    } catch {
        /* ignora */
    }
    window.location.href = "/login";
}

function redirecionarSeLogado() {
    if (obterUsuario()) window.location.href = "/painel";
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
