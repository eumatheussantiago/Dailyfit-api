// Mostra uma única vez o código de recuperação que a tela anterior deixou no sessionStorage

const dados = lerCodigoNovo();

if (dados) {
    document.getElementById("codigo").textContent = dados.codigo;
    document.getElementById("continuar").href = dados.depois;

    const copiar = document.getElementById("copiar");
    copiar.hidden = !navigator.clipboard;
    copiar.addEventListener("click", async () => {
        try {
            await navigator.clipboard.writeText(dados.codigo);
            avisar("Código copiado");
        } catch {
            avisar("Não deu para copiar: anote o código");
        }
    });
} else {
    document.getElementById("explicacao").textContent =
        "Não há código para mostrar: ele aparece uma única vez, logo depois de ser criado.";
    document.getElementById("continuar").textContent = "Continuar";
    document.getElementById("continuar").href = obterUsuario() ? "/painel" : "/login";
}
