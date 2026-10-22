// Tela de refeições: cadastro, edição, exclusão e histórico

const usuario = exigirLogin();

const base = `/usuarios/${usuario?.id}`;
const form = document.getElementById("form-refeicao");
const lista = document.getElementById("lista");
const btnSalvar = document.getElementById("btn-salvar");
const btnCancelar = document.getElementById("btn-cancelar");
const formTitulo = document.getElementById("form-titulo");

let editandoId = null;

// Se o login tiver vencido, a função api() já leva o usuário de volta para a tela de login.
async function carregarRefeicoes() {
    try {
        desenharLista(await api(`${base}/refeicoes`));
    } catch (erro) {
        avisar(erro.message);
    }
}

function desenharLista(refeicoes) {
    lista.replaceChildren();
    document.getElementById("vazia").hidden = refeicoes.length > 0;

    for (const refeicao of refeicoes) {
        const item = criarItemRefeicao(refeicao);

        const acoes = document.createElement("div");
        acoes.className = "refeicao-acoes";

        const editar = document.createElement("button");
        editar.type = "button";
        editar.textContent = "Editar";
        editar.addEventListener("click", () => comecarEdicao(refeicao));

        const apagar = document.createElement("button");
        apagar.type = "button";
        apagar.className = "apagar";
        apagar.textContent = "Excluir";
        apagar.addEventListener("click", () => excluir(refeicao));

        acoes.append(editar, apagar);
        item.append(acoes);
        lista.append(item);
    }
}

function comecarEdicao(refeicao) {
    editandoId = refeicao.id;
    form.nome.value = refeicao.nome;
    form.descricao.value = refeicao.descricao || "";
    form.dieta.value = refeicao.nao_dieta ? "nao" : "sim";
    formTitulo.textContent = "Editar refeição";
    btnSalvar.textContent = "Salvar alterações";
    btnCancelar.hidden = false;
    form.scrollIntoView({ behavior: "smooth", block: "start" });
    form.nome.focus();
}

function limparFormulario() {
    editandoId = null;
    form.reset();
    formTitulo.textContent = "Nova refeição";
    btnSalvar.textContent = "Adicionar refeição";
    btnCancelar.hidden = true;
    esconderErro("erro");
}

btnCancelar.addEventListener("click", limparFormulario);

form.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    esconderErro("erro");
    btnSalvar.disabled = true;

    const dados = {
        nome: form.nome.value,
        descricao: form.descricao.value,
        nao_dieta: form.dieta.value === "nao",
    };

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
    } catch (erro) {
        avisar(erro.message);
    }
}

if (usuario) carregarRefeicoes();
