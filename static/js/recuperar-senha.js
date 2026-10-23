// Recuperar senha: e-mail + código de recuperação + nova senha

const form = document.getElementById("form-recuperar");
const novaSenha = document.getElementById("nova-senha");
const confirmar = document.getElementById("confirmar");

form.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    esconderErro("erro");
    confirmar.setCustomValidity(confirmar.value !== novaSenha.value ? "As senhas não são iguais." : "");
    if (!form.reportValidity()) return;

    const botao = document.getElementById("btn-salvar");
    botao.disabled = true;
    try {
        const usuario = await api("/usuarios/recuperar-senha", {
            method: "POST",
            body: { email: form.email.value, codigo: form.codigo.value, nova_senha: novaSenha.value },
        });
        mostrarCodigoNovo(usuario, destinoAposEntrar(usuario));
    } catch (erro) {
        mostrarErro("erro", erro.message);
        botao.disabled = false;
    }
});

confirmar.addEventListener("input", () => confirmar.setCustomValidity(""));
