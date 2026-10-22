// Tela de progresso: números da dieta, porcentagem e melhor sequência

const usuario = exigirLogin();

async function carregarProgresso() {
    try {
        const r = await api(`/usuarios/${usuario.id}/resumo`);
        const total = r.total_refeicoes_cadastradas;
        const dentro = r.total_refeicoes_dentro_da_dieta;
        const porcentagem = total ? Math.round((dentro / total) * 100) : 0;

        document.getElementById("r-total").textContent = total;
        document.getElementById("r-dentro").textContent = dentro;
        document.getElementById("r-fora").textContent = r.total_refeicoes_fora_da_dieta;
        document.getElementById("r-sequencia").textContent = r.melhor_sequencia_de_refeicoes_dentro_da_dieta;
        document.getElementById("r-porcentagem").textContent = `${porcentagem}%`;
        document.getElementById("r-barra").style.width = `${porcentagem}%`;
    } catch (erro) {
        avisar(erro.message);
    }
}

if (usuario) carregarProgresso();
