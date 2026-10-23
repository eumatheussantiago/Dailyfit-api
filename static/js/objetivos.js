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
    document.getElementById("frase").textContent = refeicoes.length
        ? "Continue avançando: cada refeição registrada conta."
        : "Registre a primeira refeição para começar.";
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

async function carregarObjetivos() {
    const base = `/usuarios/${usuario.id}`;

    try {
        const [perfil, refeicoes] = await Promise.all([
            api(`${base}/perfil`).catch(() => null), // 404 = formulário ainda não respondido
            api(`${base}/refeicoes`),
        ]);

        document.getElementById("sem-perfil").hidden = Boolean(perfil);
        document.getElementById("com-perfil").hidden = !perfil;
        if (!perfil) return;

        document.getElementById("obj-nome").textContent = OBJETIVOS[perfil.objetivo] || perfil.objetivo;
        desenharPeso(perfil);
        desenharRotina(perfil, refeicoes);
        desenharPlano(perfil);
        desenharContou(perfil);
    } catch (erro) {
        avisar(erro.message);
    }
}

if (usuario) carregarObjetivos();
