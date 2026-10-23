// Tela de login: confere e-mail e senha no banco

redirecionarSeLogado();

const formLogin = document.getElementById("formulario-login");
const mensagemLogin = document.getElementById("mensagem-login");
const campoSenhaLogin = document.getElementById("senha");
const botaoMostrar = document.getElementById("mostrar-senha");

// Botão "Mostrar / Ocultar" senha
botaoMostrar.addEventListener("click", () => {
    const visivel = campoSenhaLogin.type === "text";
    campoSenhaLogin.type = visivel ? "password" : "text";
    botaoMostrar.textContent = visivel ? "Mostrar" : "Ocultar";
    botaoMostrar.setAttribute("aria-label", visivel ? "Mostrar senha" : "Ocultar senha");
});

// "Esqueci minha senha" (o link do grupo tem href="#") leva para a recuperação com o código
document.getElementById("recuperar-senha").addEventListener("click", (evento) => {
    evento.preventDefault();
    window.location.href = "/recuperar-senha";
});

formLogin.addEventListener("submit", async (evento) => {
    evento.preventDefault();

    if (!formLogin.reportValidity()) return;

    const botao = formLogin.querySelector("button[type=submit]");
    botao.disabled = true;
    mostrarMensagem(mensagemLogin, "Entrando...", "info");

    try {
        const usuario = await api("/usuarios/login", {
            method: "POST",
            body: {
                email: formLogin.email.value,
                senha: campoSenhaLogin.value,
            },
        });

        salvarUsuario(usuario, formLogin.lembrar.checked);
        window.location.href = destinoAposEntrar(usuario);
    } catch (erro) {
        mostrarMensagem(mensagemLogin, erro.message);
        botao.disabled = false;
    }
});
