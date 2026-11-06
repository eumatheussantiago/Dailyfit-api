// Tela de cadastro: salva o usuário no banco e segue para o formulário inicial

redirecionarSeLogado();

const formCadastro = document.getElementById("formulario-cadastro");
const mensagemCadastro = document.getElementById("mensagem-cadastro");
const campoSenha = document.getElementById("senha");
const campoConfirmar = document.getElementById("confirmar-senha");

// Avisa na hora se as senhas forem diferentes ou curtas demais
function validarSenhas() {
    campoSenha.setCustomValidity(
        campoSenha.value.length > 0 && campoSenha.value.length < 6
            ? "A senha precisa ter pelo menos 6 caracteres."
            : ""
    );
    campoConfirmar.setCustomValidity(
        campoConfirmar.value && campoConfirmar.value !== campoSenha.value
            ? "As senhas não são iguais."
            : ""
    );
}

campoSenha.addEventListener("input", validarSenhas);
campoConfirmar.addEventListener("input", validarSenhas);

formCadastro.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    validarSenhas();

    if (!formCadastro.reportValidity()) return;

    const botao = formCadastro.querySelector("button[type=submit]");
    botao.disabled = true;
    mostrarMensagem(mensagemCadastro, "Criando sua conta...", "info");

    const demora = setTimeout(() => mostrarMensagem(mensagemCadastro, AVISO_DEMORA, "info"), 8000);
    try {
        const usuario = await api("/usuarios", {
            method: "POST",
            body: {
                nome: formCadastro.nome.value,
                email: formCadastro.email.value,
                senha: campoSenha.value,
            },
        });
        clearTimeout(demora);

        mostrarMensagem(mensagemCadastro, "Conta criada! Vamos conhecer você.", "sucesso");
        mostrarCodigoNovo(usuario, "/formulario"); // antes do formulário, mostra o código de recuperação
    } catch (erro) {
        clearTimeout(demora);
        mostrarMensagem(mensagemCadastro, erro.message);
        botao.disabled = false;
    }
});
