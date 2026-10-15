// Tela do painel: resumo + cadastro, edição e exclusão de refeições

const usuario = obterUsuario();
if (!usuario) window.location.href = "/login";

const base = `/usuarios/${usuario?.id}`;
const form = document.getElementById("form-refeicao");
const lista = document.getElementById("lista");
const btnSalvar = document.getElementById("btn-salvar");
const btnCancelar = document.getElementById("btn-cancelar");
const formTitulo = document.getElementById("form-titulo");

let refeicoes = [];
let editandoId = null;

document.getElementById("ola").textContent = `Olá, ${usuario?.nome?.split(" ")[0] || ""}`;
document.getElementById("sair").addEventListener("click", sair);

const formatarData = new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
});

async function iniciar() {
    try {
        await api(base); // confirma que a conta ainda existe
    } catch {
        sair();
        return;
    }
    await atualizarTudo();
}

async function atualizarTudo() {
    try {
        const [lista, resumo] = await Promise.all([
            api(`${base}/refeicoes`),
            api(`${base}/resumo`),
        ]);
        refeicoes = lista;
        desenharLista();
        desenharResumo(resumo);
    } catch (erro) {
        avisar(erro.message);
    }
}

function desenharResumo(r) {
    const total = r.total_refeicoes_cadastradas;
    const dentro = r.total_refeicoes_dentro_da_dieta;
    const porcentagem = total ? Math.round((dentro / total) * 100) : 0;

    document.getElementById("r-total").textContent = total;
    document.getElementById("r-dentro").textContent = dentro;
    document.getElementById("r-fora").textContent = r.total_refeicoes_fora_da_dieta;
    document.getElementById("r-sequencia").textContent = r.melhor_sequencia_de_refeicoes_dentro_da_dieta;
    document.getElementById("r-porcentagem").textContent = `${porcentagem}%`;
    document.getElementById("r-barra").style.width = `${porcentagem}%`;
}

function desenharLista() {
    lista.replaceChildren();
    document.getElementById("vazia").hidden = refeicoes.length > 0;

    for (const refeicao of refeicoes) {
        const item = document.createElement("li");
        item.className = "refeicao-item";

        const info = document.createElement("div");
        info.className = "refeicao-info";

        const nome = document.createElement("strong");
        nome.textContent = refeicao.nome;

        const data = document.createElement("small");
        data.textContent = formatarData.format(new Date(refeicao.data_hora));

        info.append(nome, data);

        if (refeicao.descricao) {
            const desc = document.createElement("p");
            desc.textContent = refeicao.descricao;
            info.append(desc);
        }

        const selo = document.createElement("span");
        selo.className = refeicao.nao_dieta ? "selo selo-fora" : "selo selo-dentro";
        selo.textContent = refeicao.nao_dieta ? "Fora da dieta" : "Na dieta";

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
        item.append(info, selo, acoes);
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
        await atualizarTudo();
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
        await atualizarTudo();
    } catch (erro) {
        avisar(erro.message);
    }
}

if (usuario) iniciar();
