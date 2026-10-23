// Painel "Hoje": o progresso do dia, o plano montado com os horários do
// formulário inicial, os dias seguidos, a semana e o objetivo

const usuario = exigirLogin();

const OBJETIVOS = {
    emagrecimento: "Emagrecimento",
    ganho_massa: "Ganho de massa muscular",
    manutencao: "Manutenção do peso",
    reeducacao: "Reeducação alimentar",
};

// Refeições do plano: as que têm horário no formulário (café, almoço e jantar)
const PLANO = TIPOS_REFEICAO.filter((tipo) => tipo.campo);
const formatarDiaSemana = new Intl.DateTimeFormat("pt-BR", { weekday: "short" });

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

// Itens do plano: as refeições do formulário (feitas ou não) + as outras registradas hoje
function montarPlano(perfil, doDia) {
    const restantes = [...doDia];
    const itens = [];

    for (const p of PLANO) {
        if (!perfil?.[p.campo]) continue;
        const i = restantes.findIndex((r) => simplificar(r.nome).includes(p.chave));
        itens.push({ ...p, horario: perfil[p.campo], refeicao: i >= 0 ? restantes.splice(i, 1)[0] : null });
    }
    for (const r of restantes) {
        itens.push({ nome: r.nome, icone: tipoDaRefeicao(r.nome)?.icone || "🍽️", refeicao: r });
    }

    // Refeição do plano fica no lugar do horário planejado, mesmo registrada mais tarde
    for (const item of itens) {
        item.hora = item.refeicao ? formatarHora.format(new Date(item.refeicao.data_hora)) : item.horario;
    }
    return itens.sort((a, b) => (a.horario || a.hora).localeCompare(b.horario || b.hora));
}

function criarItemPlano({ nome, icone, refeicao, hora }) {
    const item = document.createElement("li");
    item.className = "meal";

    const iconeEl = document.createElement("div");
    iconeEl.className = "meal-icon";
    iconeEl.setAttribute("aria-hidden", "true");
    iconeEl.textContent = icone;

    const info = document.createElement("div");
    info.className = "meal-info";
    const nomeEl = document.createElement("strong");
    nomeEl.textContent = nome;
    const quando = document.createElement("small");
    quando.textContent = refeicao
        ? `Registrado às ${hora}${refeicao.nao_dieta ? " · fora da dieta" : ""}`
        : `Planejado para ${hora}`;
    info.append(nomeEl, quando);

    let fim;
    if (refeicao) {
        fim = document.createElement("span");
        fim.className = refeicao.nao_dieta ? "meal-check fora" : "meal-check";
        fim.textContent = "✓";
    } else {
        fim = document.createElement("a");
        fim.className = "meal-arrow";
        fim.href = `/refeicoes?nome=${encodeURIComponent(nome)}`;
        fim.setAttribute("aria-label", `Registrar ${nome}`);
        fim.textContent = "→";
    }

    item.append(iconeEl, info, fim);
    return item;
}

function desenharHoje(perfil, doDia, meta) {
    const feitas = doDia.length;
    const pct = Math.min(100, Math.round((feitas / meta) * 100));
    const faltam = meta - feitas;

    document.getElementById("hoje").style.setProperty("--p", `${pct}%`);
    document.getElementById("pct").textContent = `${pct}%`;
    document.getElementById("hoje-total").textContent = `${feitas} de ${meta}`;
    document.getElementById("hoje-dentro").textContent = doDia.filter((r) => !r.nao_dieta).length;
    document.getElementById("status").lastChild.textContent =
        feitas === 0 ? "Começando" : faltam > 0 ? "Em andamento" : "Dia completo";
    document.getElementById("frase").textContent =
        feitas === 0
            ? "Nenhuma refeição registrada hoje. Comece pela próxima."
            : faltam > 0
              ? `Faltam ${plural(faltam, "refeição", "refeições")} para completar o dia.`
              : "Dia completo. Amanhã tem mais.";

    const plano = montarPlano(perfil, doDia);
    document.getElementById("plano").replaceChildren(...plano.map(criarItemPlano));
}

function desenharSemana(refeicoes, meta) {
    const porDia = new Map();
    for (const r of refeicoes) {
        const chave = chaveDia(r.data_hora);
        porDia.set(chave, (porDia.get(chave) || 0) + 1);
    }

    // Conta só os dias desde a primeira refeição: quem começou ontem não fica com a semana "vazia"
    const inicio = refeicoes.length ? meiaNoite(refeicoes.at(-1).data_hora) : meiaNoite(new Date());
    const semana = [6, 5, 4, 3, 2, 1, 0].map((n) => {
        const data = diasAtras(n);
        return { data, total: porDia.get(data.getTime()) || 0, conta: data >= inicio };
    });

    document.getElementById("semana").replaceChildren(
        ...semana.map(({ data, total }) => {
            const coluna = document.createElement("div");
            const barra = document.createElement("span");
            barra.style.height = `${4 + Math.round(32 * Math.min(total / meta, 1))}px`;
            coluna.append(barra, formatarDiaSemana.format(data).replace(".", ""));
            return coluna;
        })
    );

    const totalSemana = semana.reduce((soma, d) => soma + d.total, 0);
    document.getElementById("semana-total").textContent = plural(totalSemana, "refeição", "refeições");

    // Rotina = refeições feitas / planejadas nos dias contados (dia com refeição a mais não compensa outro)
    const contados = semana.filter((d) => d.conta);
    const feitas = contados.reduce((soma, d) => soma + Math.min(d.total, meta), 0);
    const rotina = Math.round((feitas / (meta * Math.max(contados.length, 1))) * 100);
    document.getElementById("rotina-pct").textContent = `${rotina}%`;
    document.getElementById("rotina-barra").style.width = `${rotina}%`;

    document.getElementById("seq").textContent = plural(diasSeguidos(new Set(porDia.keys())), "dia", "dias");
}

function desenharObjetivo(perfil) {
    const nome = document.getElementById("obj-nome");
    const peso = document.getElementById("obj-peso");

    if (!perfil) {
        nome.textContent = "Responda o formulário inicial";
        peso.textContent = "Com ele o DailyFit monta o seu plano do dia.";
        document.getElementById("obj-link").textContent = "Responder agora";
        return;
    }

    const kg = (valor) => `${Number(valor).toLocaleString("pt-BR")} kg`;
    nome.textContent = OBJETIVOS[perfil.objetivo] || perfil.objetivo;
    peso.textContent = perfil.peso_meta
        ? `Peso informado: ${kg(perfil.peso_atual)} · meta: ${kg(perfil.peso_meta)}`
        : `Peso informado: ${kg(perfil.peso_atual)}`;
}

async function carregarPainel() {
    const base = `/usuarios/${usuario.id}`;
    const hoje = new Intl.DateTimeFormat("pt-BR", { weekday: "long", day: "numeric", month: "long" });
    document.getElementById("data-hoje").textContent = hoje.format(new Date()).toUpperCase();

    try {
        const [refeicoes, perfil] = await Promise.all([
            api(`${base}/refeicoes`),
            api(`${base}/perfil`).catch(() => null), // 404 = formulário ainda não respondido
        ]);

        // Sem formulário respondido, usa o mínimo que ele oferece (3 refeições por dia)
        const meta = perfil?.refeicoes_por_dia || 3;
        const chaveHoje = chaveDia(new Date());
        // A API devolve da mais recente para a mais antiga; o plano lê na ordem do dia
        const doDia = refeicoes.filter((r) => chaveDia(r.data_hora) === chaveHoje).reverse();

        desenharHoje(perfil, doDia, meta);
        desenharSemana(refeicoes, meta);
        desenharObjetivo(perfil);
    } catch (erro) {
        avisar(erro.message);
    }
}

if (usuario) carregarPainel();
