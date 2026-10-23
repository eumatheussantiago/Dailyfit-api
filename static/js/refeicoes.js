// Tela de refeições: atalhos de nome, cadastro, edição, exclusão e histórico por dia

const usuario = exigirLogin();

const base = `/usuarios/${usuario?.id}`;
const form = document.getElementById("form-refeicao");
const lista = document.getElementById("lista");
const btnSalvar = document.getElementById("btn-salvar");
const btnCancelar = document.getElementById("btn-cancelar");
const formTitulo = document.getElementById("form-titulo");
const atalhos = document.getElementById("atalhos");
const formatarDia = new Intl.DateTimeFormat("pt-BR", { weekday: "long", day: "numeric", month: "long" });

let editandoId = null;

// Valor do campo datetime-local ("2026-10-23T12:30") no horário do navegador
const doisDigitos = (n) => String(n).padStart(2, "0");
const valorDataLocal = (d) =>
    `${d.getFullYear()}-${doisDigitos(d.getMonth() + 1)}-${doisDigitos(d.getDate())}T${doisDigitos(d.getHours())}:${doisDigitos(d.getMinutes())}`;

// O calendário do campo só oferece os últimos 30 dias até agora (a API recusa o resto)
function limitarCampoQuando() {
    const agora = new Date();
    form.quando.max = valorDataLocal(agora);
    form.quando.min = valorDataLocal(new Date(agora.getTime() - 30 * 24 * 60 * 60 * 1000));
}
form.quando.addEventListener("focus", limitarCampoQuando);

// Atalhos com os tipos que o Painel reconhece: o nome escolhido entra no plano do dia
for (const tipo of TIPOS_REFEICAO) {
    const botao = document.createElement("button");
    botao.type = "button";
    botao.dataset.nome = tipo.nome;
    const icone = document.createElement("span");
    icone.setAttribute("aria-hidden", "true");
    icone.textContent = tipo.icone;
    botao.append(icone, ` ${tipo.nome}`);
    botao.addEventListener("click", () => {
        form.nome.value = tipo.nome;
        marcarAtalho();
        form.descricao.focus();
    });
    atalhos.append(botao);
}

// Destaca o atalho do tipo que o nome digitado já é
function marcarAtalho() {
    const tipo = tipoDaRefeicao(form.nome.value);
    for (const botao of atalhos.children) {
        botao.setAttribute("aria-pressed", String(botao.dataset.nome === tipo?.nome));
    }
}

form.nome.addEventListener("input", marcarAtalho);

// Se o login tiver vencido, a função api() já leva o usuário de volta para a tela de login.
async function carregarRefeicoes() {
    try {
        desenharLista(await api(`${base}/refeicoes`));
    } catch (erro) {
        avisar(erro.message);
    }
}

function nomeDoDia(data) {
    if (chaveDia(data) === chaveDia(new Date())) return "Hoje";
    if (chaveDia(data) === diasAtras(1).getTime()) return "Ontem";
    return formatarDia.format(data);
}

// A API devolve da mais recente para a mais antiga: cada dia vira um grupo, na mesma ordem
function desenharLista(refeicoes) {
    document.getElementById("vazia").hidden = refeicoes.length > 0;

    const dias = new Map();
    for (const refeicao of refeicoes) {
        const chave = chaveDia(refeicao.data_hora);
        if (!dias.has(chave)) dias.set(chave, []);
        dias.get(chave).push(refeicao);
    }

    lista.replaceChildren(
        ...[...dias].map(([chave, doDia]) => {
            const grupo = document.createElement("section");
            grupo.className = "dia-grupo";

            const titulo = document.createElement("h3");
            const resumo = document.createElement("small");
            const dentro = doDia.filter((r) => !r.nao_dieta).length;
            resumo.textContent = `${plural(doDia.length, "refeição", "refeições")} · ${dentro} na dieta`;
            titulo.append(nomeDoDia(new Date(chave)), " ", resumo);

            const itens = document.createElement("ul");
            itens.append(...doDia.map(criarItemComAcoes));
            grupo.append(titulo, itens);
            return grupo;
        })
    );
}

function criarItemComAcoes(refeicao) {
    const item = criarItemRefeicao(refeicao);
    // Vários "Editar"/"Excluir" na lista: o nome acessível diz de qual refeição é
    const qual = `${refeicao.nome} das ${formatarHora.format(new Date(refeicao.data_hora))}`;

    const acoes = document.createElement("div");
    acoes.className = "refeicao-acoes";

    const editar = document.createElement("button");
    editar.type = "button";
    editar.textContent = "Editar";
    editar.setAttribute("aria-label", `Editar ${qual}`);
    editar.addEventListener("click", () => comecarEdicao(refeicao));

    const apagar = document.createElement("button");
    apagar.type = "button";
    apagar.className = "apagar";
    apagar.textContent = "Excluir";
    apagar.setAttribute("aria-label", `Excluir ${qual}`);
    apagar.addEventListener("click", () => excluir(refeicao));

    acoes.append(editar, apagar);
    item.append(acoes);
    return item;
}

function comecarEdicao(refeicao) {
    editandoId = refeicao.id;
    form.nome.value = refeicao.nome;
    form.descricao.value = refeicao.descricao || "";
    form.quando.value = valorDataLocal(new Date(refeicao.data_hora));
    form.quando.dataset.original = form.quando.value;
    form.dieta.value = refeicao.nao_dieta ? "nao" : "sim";
    marcarAtalho();
    formTitulo.textContent = "Editar refeição";
    btnSalvar.textContent = "Salvar alterações";
    btnCancelar.hidden = false;
    form.scrollIntoView({ behavior: "smooth", block: "start" });
    form.nome.focus();
}

function limparFormulario() {
    editandoId = null;
    form.reset();
    form.quando.dataset.original = "";
    marcarAtalho();
    formTitulo.textContent = "Nova refeição";
    btnSalvar.textContent = "Adicionar refeição";
    btnCancelar.hidden = true;
    esconderErro("erro");
}

// O botão some ao cancelar: o foco volta para o formulário em vez de ir para o topo da página
btnCancelar.addEventListener("click", () => {
    limparFormulario();
    form.nome.focus();
});

form.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    esconderErro("erro");
    btnSalvar.disabled = true;

    const dados = {
        nome: form.nome.value,
        descricao: form.descricao.value,
        nao_dieta: form.dieta.value === "nao",
    };
    // Vazio: ao criar vale a hora do registro; ao editar a API mantém a hora que já estava.
    // O campo vem no horário local; a API recebe com fuso (toISOString é UTC).
    // Na edição, só manda se a pessoa mudou: reenviar a hora de uma refeição antiga (mais de
    // 30 dias) seria recusado e cortaria os segundos.
    if (form.quando.value && form.quando.value !== form.quando.dataset.original) {
        dados.data_hora = new Date(form.quando.value).toISOString();
    }

    try {
        if (editandoId) {
            await api(`${base}/refeicoes/${editandoId}`, { method: "PUT", body: dados });
            avisar("Refeição atualizada");
        } else {
            await api(`${base}/refeicoes`, { method: "POST", body: dados });
            avisar("Refeição adicionada");
        }
        limparFormulario();
        await carregarRefeicoes();
    } catch (erro) {
        mostrarErro("erro", erro.message);
    } finally {
        btnSalvar.disabled = false;
    }
});

async function excluir(refeicao) {
    if (!confirm(`Excluir "${refeicao.nome}"?`)) return;

    try {
        await api(`${base}/refeicoes/${refeicao.id}`, { method: "DELETE" });
        if (editandoId === refeicao.id) limparFormulario();
        avisar("Refeição excluída");
        await carregarRefeicoes();
        document.getElementById("historico-titulo").focus(); // o item com foco foi apagado
    } catch (erro) {
        avisar(erro.message);
    }
}

// Vindo do Painel (seta de uma refeição do plano), o nome já chega preenchido
const nomeSugerido = new URLSearchParams(location.search).get("nome");
if (nomeSugerido) form.nome.value = nomeSugerido.slice(0, 100);
marcarAtalho();

if (usuario) carregarRefeicoes();
