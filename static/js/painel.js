// Tela do painel: resumo e as 5 refeições mais recentes

const usuario = exigirLogin();

async function carregarPainel() {
    const base = `/usuarios/${usuario.id}`;

    try {
        const [refeicoes, resumo] = await Promise.all([
            api(`${base}/refeicoes`),
            api(`${base}/resumo`),
        ]);

        document.getElementById("r-total").textContent = resumo.total_refeicoes_cadastradas;
        document.getElementById("r-dentro").textContent = resumo.total_refeicoes_dentro_da_dieta;
        document.getElementById("r-fora").textContent = resumo.total_refeicoes_fora_da_dieta;

        // A API já devolve da mais recente para a mais antiga
        document.getElementById("vazia").hidden = refeicoes.length > 0;
        document.getElementById("lista").replaceChildren(...refeicoes.slice(0, 5).map(criarItemRefeicao));
    } catch (erro) {
        avisar(erro.message);
    }
}

if (usuario) carregarPainel();
