// Tela de progresso: 7 dias × 7 dias anteriores, dias seguidos, gráfico de 14 dias e o total

const usuario = exigirLogin();

const formatarDiaCurto = new Intl.DateTimeFormat("pt-BR", { weekday: "short", day: "2-digit", month: "2-digit" });

// Soma 7 dias a partir de n dias atrás (n = 0: os últimos 7 dias, contando hoje)
function somarSemana(porDia, n) {
    const soma = { total: 0, dentro: 0 };
    for (let i = n; i < n + 7; i++) {
        const dia = porDia.get(diasAtras(i).getTime());
        soma.total += dia?.total || 0;
        soma.dentro += dia?.dentro || 0;
    }
    return soma;
}

const porcentagemDieta = ({ total, dentro }) => (total ? Math.round((dentro / total) * 100) : null);

function textoVariacao(atual, anterior) {
    if (!anterior) return atual ? "Nada registrado nos 7 dias anteriores" : "Nada registrado nos últimos 14 dias";
    const variacao = Math.round(((atual - anterior) / anterior) * 100);
    if (variacao === 0) return "Igual aos 7 dias anteriores";
    return `${variacao > 0 ? "+" : "−"}${Math.abs(variacao)}% em relação aos 7 dias anteriores`;
}

// Do meio-dia, pelo mesmo motivo de diasAtras() no app.js
function diaSeguinte(chave) {
    const d = new Date(chave);
    d.setHours(12, 0, 0, 0);
    d.setDate(d.getDate() + 1);
    return meiaNoite(d).getTime();
}

// Maior número de dias seguidos com registro, em toda a história
function melhorSequenciaDeDias(porDia) {
    let melhor = 0;
    let atual = 0;
    let anterior = null;
    for (const chave of [...porDia.keys()].sort((a, b) => a - b)) {
        atual = anterior !== null && diaSeguinte(anterior) === chave ? atual + 1 : 1;
        melhor = Math.max(melhor, atual);
        anterior = chave;
    }
    return melhor;
}

// Barras empilhadas: na dieta embaixo, fora da dieta em cima; altura pelo dia com mais refeições
function desenharGrafico(porDia) {
    const dias = Array.from({ length: 14 }, (_, i) => diasAtras(13 - i));
    const maximo = Math.max(1, ...dias.map((data) => porDia.get(data.getTime())?.total || 0));
    const descricoes = [];

    document.getElementById("grafico").replaceChildren(
        ...dias.map((data) => {
            const { total = 0, dentro = 0 } = porDia.get(data.getTime()) || {};
            const descricao = `${formatarDiaCurto.format(data)}: ${plural(total, "refeição", "refeições")}, ${dentro} na dieta`;
            descricoes.push(descricao);

            const coluna = document.createElement("div");
            coluna.className = "coluna";
            coluna.title = descricao;

            const valor = document.createElement("small");
            valor.textContent = total || "";

            const barra = document.createElement("div");
            barra.className = "barra";
            barra.style.height = `${Math.round((120 * total) / maximo)}px`;
            for (const [classe, quantidade] of [["fora", total - dentro], ["dentro", dentro]]) {
                if (!quantidade) continue;
                const parte = document.createElement("span");
                parte.className = classe;
                parte.style.flexGrow = quantidade;
                barra.append(parte);
            }

            const rotulo = document.createElement("span");
            rotulo.className = "rotulo";
            rotulo.textContent = data.getDate();

            coluna.append(valor, barra, rotulo);
            return coluna;
        })
    );

    document.getElementById("grafico").setAttribute("aria-label", `Refeições por dia nos últimos 14 dias. ${descricoes.join("; ")}.`);
}

async function carregarProgresso() {
    const base = `/usuarios/${usuario.id}`;

    try {
        const [refeicoes, resumo] = await Promise.all([api(`${base}/refeicoes`), api(`${base}/resumo`)]);
        const porDia = refeicoesPorDia(refeicoes);

        const semana = somarSemana(porDia, 0);
        const anterior = somarSemana(porDia, 7);
        const dietaSemana = porcentagemDieta(semana);
        const dietaAnterior = porcentagemDieta(anterior);

        document.getElementById("semana-total").textContent = plural(semana.total, "refeição", "refeições");
        document.getElementById("semana-variacao").textContent = textoVariacao(semana.total, anterior.total);
        document.getElementById("semana-dieta").textContent = dietaSemana === null ? "—" : `${dietaSemana}%`;
        document.getElementById("semana-dieta-antes").textContent =
            dietaAnterior === null ? "Sem registros nos 7 dias anteriores" : `Nos 7 dias anteriores: ${dietaAnterior}%`;

        document.getElementById("seq-atual").textContent = plural(diasSeguidos(porDia), "dia", "dias");
        document.getElementById("seq-melhor").textContent = `Melhor sequência: ${plural(melhorSequenciaDeDias(porDia), "dia", "dias")}`;
        document.getElementById("seq-refeicoes").textContent = resumo.melhor_sequencia_de_refeicoes_dentro_da_dieta;

        desenharGrafico(porDia);

        const total = resumo.total_refeicoes_cadastradas;
        const geral = porcentagemDieta({ total, dentro: resumo.total_refeicoes_dentro_da_dieta }) || 0;
        document.getElementById("r-desde").textContent =
            `Desde o início: ${plural(total, "refeição", "refeições")} em ${plural(porDia.size, "dia", "dias")}, dentro da dieta`;
        document.getElementById("r-porcentagem").textContent = `${geral}%`;
        document.getElementById("r-barra").style.width = `${geral}%`;
    } catch (erro) {
        avisar(erro.message);
    }
}

if (usuario) carregarProgresso();
