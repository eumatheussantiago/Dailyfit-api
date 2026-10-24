const etapas = document.querySelectorAll(".form-step");
const indicadores = document.querySelectorAll(".progress-step");
const descricao = document.getElementById("etapa-descricao");
let etapaAtual = 1;

const descricoes = {
    1: "Conte um pouco sobre seus objetivos e sua rotina para ajudarmos a organizar sua experiência no DailyFit.",

    2: "Agora queremos conhecer um pouco melhor seus hábitos e preferências alimentares.",

    3: "Por fim, conte um pouco sobre sua rotina para que sua experiência seja ainda mais personalizada."
};

function mostrarEtapa(numero) {
    etapaAtual = numero;
    etapas.forEach((etapa) => {
        const numeroEtapa = Number(etapa.dataset.step);
        etapa.classList.toggle(
            "active",
            numeroEtapa === numero
        );
    });

    indicadores.forEach((indicador) => {
        const numeroIndicador = Number(indicador.dataset.step);

        indicador.classList.toggle(
            "active",
            numeroIndicador === numero
        );

        indicador.classList.toggle(
            "completed",
            numeroIndicador < numero
        );
    });
    descricao.textContent = descricoes[numero];
    window.scrollTo({
        top: 0,
        behavior: "smooth"
    });
}

function validarEtapa() {
    const etapa = document.querySelector(
        `.form-step[data-step="${etapaAtual}"]`
    );

    const campos = etapa.querySelectorAll(
        "input, select, textarea"
    );

    for (const campo of campos) {

        if (!campo.checkValidity()) {
            campo.reportValidity();
            return false;
        }
    }
    return true;
}

document.querySelectorAll(".next-step").forEach((botao) => {
    botao.addEventListener("click", () => {
        if (!validarEtapa()) {
            return;
        }

        if (etapaAtual < 3) {
            mostrarEtapa(etapaAtual + 1);
        }
    });
});

document.querySelectorAll(".prev-step").forEach((botao) => {
    botao.addEventListener("click", () => {
        if (etapaAtual > 1) {
            mostrarEtapa(etapaAtual - 1);
        }
    });
});

// ---------- Ligação com o banco de dados ----------

const usuarioLogado = obterUsuario();
if (!usuarioLogado) window.location.href = "/login";

const formularioDieta = document.getElementById("formulario-dieta");

// Mensagem de status logo abaixo do formulário
const mensagemFormulario = document.createElement("p");
mensagemFormulario.className = "login-message";
mensagemFormulario.setAttribute("role", "status");
mensagemFormulario.setAttribute("aria-live", "polite");
formularioDieta.after(mensagemFormulario);

// Campos de texto/número/horário: nome no formulário -> nome no banco
const camposSimples = {
    sexo: "sexo",
    idade: "idade",
    altura: "altura",
    peso_atual: "peso_atual",
    peso_meta: "peso_meta",
    tipo_alimentacao: "tipo_alimentacao",
    restricoes: "restricoes",
    preferencias: "preferencias",
    refeicoes: "refeicoes_por_dia",
    horario_cafe: "horario_cafe",
    horario_almoco: "horario_almoco",
    horario_jantar: "horario_jantar",
    dificuldades_rotina: "dificuldades_rotina",
};
const camposNumericos = ["idade", "altura", "peso_atual", "peso_meta", "refeicoes_por_dia"];

function lerFormulario() {
    const dados = {
        objetivo: formularioDieta.objetivo.value,
        atividade: formularioDieta.atividade.value,
    };

    for (const [campo, chave] of Object.entries(camposSimples)) {
        const valor = formularioDieta.elements[campo].value.trim();
        if (camposNumericos.includes(chave)) {
            dados[chave] = valor === "" ? null : Number(valor);
        } else {
            dados[chave] = valor === "" ? null : valor;
        }
    }
    return dados;
}

// Se o usuário já respondeu antes, mostra as respostas para ele editar
async function carregarRespostas() {
    let perfil;
    try {
        perfil = await buscarPerfil(usuarioLogado.id); // null só quando ainda não respondeu (404)
    } catch (erro) {
        mostrarMensagem(mensagemFormulario, `Não foi possível carregar suas respostas (${erro.message}). Recarregue a página antes de salvar.`);
        return;
    }
    if (!perfil) return; // ainda não respondeu: formulário começa vazio
    try {
        formularioDieta.objetivo.value = perfil.objetivo;
        formularioDieta.atividade.value = perfil.atividade;
        for (const [campo, chave] of Object.entries(camposSimples)) {
            if (perfil[chave] !== null) {
                formularioDieta.elements[campo].value = perfil[chave];
            }
        }
    } catch {
        /* algum campo do formulário mudou de nome: preenche o que der */
    }
}

formularioDieta.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    if (!validarEtapa()) {
        return;
    }

    const botao = formularioDieta.querySelector("button[type=submit]");
    botao.disabled = true;
    mostrarMensagem(mensagemFormulario, "Salvando suas respostas...", "info");

    try {
        await api(`/usuarios/${usuarioLogado.id}/perfil`, {
            method: "PUT",
            body: lerFormulario(),
        });

        salvarUsuario({ ...usuarioLogado, perfil_preenchido: true });
        mostrarMensagem(mensagemFormulario, "Formulário preenchido com sucesso!", "sucesso");
        window.location.href = "/painel";
    } catch (erro) {
        mostrarMensagem(mensagemFormulario, erro.message);
        botao.disabled = false;
    }
});

if (usuarioLogado) carregarRespostas();