// Tela de objetivos: objetivo e meta de peso, metas da rotina, plano de horários
// e o que a pessoa contou no formulário inicial

const usuario = exigirLogin();

// Mesmos textos das opções do formulário inicial
const ATIVIDADES = {
    sedentario: "Sedentário",
    levemente_ativo: "Levemente ativo",
    moderadamente_ativo: "Moderadamente ativo",
    muito_ativo: "Muito ativo",
    extremamente_ativo: "Extremamente ativo",
};
const ALIMENTACAO = {
    variada: "Alimentação variada",
    vegetariana: "Vegetariana",
    vegana: "Vegana",
    outra: "Outra alimentação",
};

const kg = (valor) => `${Number(valor).toLocaleString("pt-BR")} kg`;

function preencherBarra(id, porcentagem) {
    document.getElementById(id).style.width = `${Math.min(100, porcentagem)}%`;
}

function desenharPeso(perfil) {
    document.getElementById("peso-atual").textContent = kg(perfil.peso_atual);

    const temMeta = Boolean(perfil.peso_meta);
    document.getElementById("meta-bloco").hidden = !temMeta;
    document.getElementById("dif-bloco").hidden = !temMeta;
    if (!temMeta) return;

    // Arredonda para não mostrar 7,499999 kg
    const diferenca = Math.round((perfil.peso_meta - perfil.peso_atual) * 10) / 10;
    document.getElementById("peso-meta").textContent = kg(perfil.peso_meta);
    document.getElementById("peso-dif").textContent =
        diferenca === 0 ? "você já está nela" : `${diferenca > 0 ? "ganhar" : "perder"} ${kg(Math.abs(diferenca))}`;
}

function desenharRotina(perfil, refeicoes) {
    const meta = perfil.refeicoes_por_dia;
    const porDia = refeicoesPorDia(refeicoes);
    const hoje = porDia.get(chaveDia(new Date()))?.total || 0;
    const rotina = rotinaDaSemana(refeicoes, porDia, meta);

    document.getElementById("hoje-total").textContent = `${hoje} de ${meta}`;
    preencherBarra("hoje-barra", (hoje / meta) * 100);
    document.getElementById("rotina-pct").textContent = `${rotina}%`;
    preencherBarra("rotina-barra", rotina);
    document.getElementById("frase").textContent = !refeicoes.length
        ? "Registre a primeira refeição para começar."
        : hoje < meta
          ? `Faltam ${plural(meta - hoje, "refeição", "refeições")} para cumprir o plano de hoje.`
          : "Plano de hoje cumprido.";
}

function desenharPlano(perfil) {
    const itens = TIPOS_REFEICAO.filter((tipo) => tipo.campo && perfil[tipo.campo]).map((tipo) => {
        const item = document.createElement("li");
        item.className = "meal";

        const icone = document.createElement("div");
        icone.className = "meal-icon";
        icone.setAttribute("aria-hidden", "true");
        icone.textContent = tipo.icone;

        const info = document.createElement("div");
        info.className = "meal-info";
        const nome = document.createElement("strong");
        nome.textContent = tipo.nome;
        const hora = document.createElement("small");
        hora.textContent = `às ${perfil[tipo.campo]}`;
        info.append(nome, hora);

        item.append(icone, info);
        return item;
    });
    document.getElementById("plano").replaceChildren(...itens);

    document.getElementById("plano-resumo").textContent = [
        itens.length ? null : "Sem horários definidos",
        plural(perfil.refeicoes_por_dia, "refeição por dia", "refeições por dia"),
        ALIMENTACAO[perfil.tipo_alimentacao],
        ATIVIDADES[perfil.atividade],
    ]
        .filter(Boolean)
        .join(" · ");
}

// Números calculados pela API a partir do formulário (saude.py)
function desenharNumeros(perfil) {
    const n = perfil.indicadores;
    const num = (valor, casas = 1) => Number(valor).toLocaleString("pt-BR", { maximumFractionDigits: casas });

    document.getElementById("n-imc").textContent = num(n.imc);
    document.getElementById("n-imc-faixa").textContent =
        n.faixa_imc || "Abaixo de 20 anos, o IMC é avaliado por tabela de idade";
    document.getElementById("n-peso").textContent = `${num(n.peso_saudavel_min)} a ${num(n.peso_saudavel_max)} kg`;
    document.getElementById("n-gasto").textContent = n.gasto_calorico ? `${num(n.gasto_calorico, 0)} kcal` : "—";
    document.getElementById("n-gasto-ajuda").textContent = n.gasto_calorico
        ? "por dia, para manter o peso atual"
        : "a fórmula vale a partir de 18 anos";
    document.getElementById("n-agua").textContent = `${num(n.agua_litros)} L`;

    const meta = document.getElementById("n-meta");
    meta.hidden = !n.semanas_ate_meta;
    meta.textContent = `No ritmo de 0,5 kg por semana, a meta leva cerca de ${plural(n.semanas_ate_meta, "semana", "semanas")}.`;

    const alerta = document.getElementById("n-alerta");
    alerta.hidden = !n.meta_abaixo_do_saudavel;
    alerta.textContent = `Essa meta fica abaixo da faixa saudável para a sua altura (IMC ${num(n.imc_meta)}). Vale conversar com um nutricionista antes.`;

    document.getElementById("numeros").hidden = false;
}

// "hoje às 14:30", "amanhã às 10:00"… no horário do navegador
const formatarDiaHora = new Intl.DateTimeFormat("pt-BR", { day: "numeric", month: "long", hour: "2-digit", minute: "2-digit" });
function formatarQuando(data) {
    const hora = formatarHora.format(data);
    const dia = chaveDia(data);
    if (dia === chaveDia(new Date())) return `hoje às ${hora}`;
    if (dia === diasAtras(-1).getTime()) return `amanhã às ${hora}`;
    if (dia === diasAtras(1).getTime()) return `ontem às ${hora}`;
    return formatarDiaHora.format(data);
}

// Dicas da IA: a API guarda a última geração e diz quando dá para gerar de novo.
// Gerar exige marcar o consentimento (dado de saúde, LGPD); a API registra o aceite.
const aceite = document.getElementById("dicas-aceite");
let podeGerar = false;

function atualizarBotaoDicas() {
    document.getElementById("dicas-gerar").disabled = !(podeGerar && aceite.checked);
}
aceite.addEventListener("change", atualizarBotaoDicas);

function desenharDicas(resposta) {
    const estado = document.getElementById("dicas-estado");
    const botao = document.getElementById("dicas-gerar");
    document.getElementById("dicas").hidden = false;

    document.getElementById("dicas-lista").replaceChildren(
        ...resposta.dicas.map(({ titulo, texto }) => {
            const item = document.createElement("li");
            const tituloEl = document.createElement("strong");
            tituloEl.textContent = titulo;
            const textoEl = document.createElement("p");
            textoEl.textContent = texto;
            item.append(tituloEl, textoEl);
            return item;
        })
    );

    if (!resposta.ligadas) {
        estado.textContent = "As dicas com IA ainda não foram ligadas neste site.";
        botao.hidden = true;
        document.getElementById("dicas-aceite-rotulo").hidden = true;
        return;
    }

    const proxima = resposta.proxima_em ? new Date(resposta.proxima_em) : null;
    const esperar = proxima && proxima > new Date();
    estado.textContent = resposta.criado_em
        ? `Geradas ${formatarQuando(new Date(resposta.criado_em))}.`
        : "Gere dicas feitas para você a partir do seu formulário e das refeições da semana.";
    botao.hidden = false;
    document.getElementById("dicas-aceite-rotulo").hidden = Boolean(esperar);
    podeGerar = !esperar;
    atualizarBotaoDicas();
    botao.textContent = esperar
        ? `Novas dicas ${formatarQuando(proxima)}`
        : resposta.criado_em
          ? "Gerar novas dicas"
          : "Gerar dicas";
}

async function carregarDicas(perfil) {
    if (perfil.idade < 18) {
        // LGPD art. 14: dado de saúde de menor não vai para a IA (a API também recusa)
        document.getElementById("dicas").hidden = false;
        document.getElementById("dicas-estado").textContent = "As dicas com IA são só para maiores de 18 anos.";
        return;
    }
    try {
        desenharDicas(await api(`/usuarios/${usuario.id}/dicas`));
    } catch (erro) {
        avisar(erro.message);
    }
}

document.getElementById("dicas-gerar").addEventListener("click", async () => {
    const estado = document.getElementById("dicas-estado");
    const botao = document.getElementById("dicas-gerar");
    botao.disabled = true;
    botao.textContent = "Gerando dicas…";
    estado.textContent = "A IA está escrevendo suas dicas. Leva alguns segundos.";
    try {
        desenharDicas(
            await api(`/usuarios/${usuario.id}/dicas`, { method: "POST", body: { consentimento: aceite.checked } })
        );
        document.getElementById("dicas-titulo").focus();
    } catch (erro) {
        estado.textContent = erro.message;
        atualizarBotaoDicas();
        botao.textContent = "Tentar de novo";
    }
});

// Respostas de texto livre: só aparecem as que foram preenchidas
function desenharContou(perfil) {
    const campos = [
        ["Restrições", perfil.restricoes],
        ["Preferências", perfil.preferencias],
        ["Dificuldades na rotina", perfil.dificuldades_rotina],
    ].filter(([, texto]) => texto);

    document.getElementById("contou").hidden = campos.length === 0;
    document.getElementById("contou-lista").replaceChildren(
        ...campos.flatMap(([rotulo, texto]) => {
            const termo = document.createElement("dt");
            termo.textContent = rotulo;
            const valor = document.createElement("dd");
            valor.textContent = texto;
            return [termo, valor];
        })
    );
}

// Mostra o perfil assim que ele chega; as metas da rotina entram quando as refeições chegarem
async function carregarObjetivos() {
    const carregando = document.getElementById("carregando");

    try {
        const perfil = await buscarPerfil(usuario.id);
        carregando.hidden = true;
        document.getElementById("sem-perfil").hidden = Boolean(perfil);
        document.getElementById("com-perfil").hidden = !perfil;
        if (!perfil) return;

        document.getElementById("obj-nome").textContent = OBJETIVOS[perfil.objetivo] || perfil.objetivo;
        desenharPeso(perfil);
        desenharNumeros(perfil);
        desenharPlano(perfil);
        desenharContou(perfil);
        carregarDicas(perfil); // sem await: as dicas não seguram o resto da tela
        desenharRotina(perfil, await api(`/usuarios/${usuario.id}/refeicoes`));
    } catch (erro) {
        avisar(erro.message);
        carregando.textContent = `Não foi possível carregar seus dados: ${erro.message}`;
        carregando.hidden = false;
    }
}

document.getElementById("novo-codigo").addEventListener("click", async (evento) => {
    const botao = evento.currentTarget; // depois do await, currentTarget já é null
    if (!confirm("Gerar um código novo? O código anterior deixa de valer.")) return;
    botao.disabled = true;
    try {
        const resposta = await api(`/usuarios/${usuario.id}/codigo-recuperacao`, { method: "POST" });
        mostrarCodigoNovo(resposta, "/objetivos");
    } catch (erro) {
        avisar(erro.message);
        botao.disabled = false;
    }
});

if (usuario) carregarObjetivos();
