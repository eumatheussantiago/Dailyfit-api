from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class UsuarioCreate(BaseModel):
    nome: str = Field(min_length=2, max_length=100)
    email: str = Field(max_length=255)
    senha: str = Field(min_length=6, max_length=128)

    @field_validator("nome")
    @classmethod
    def limpar_nome(cls, valor: str) -> str:
        valor = valor.strip()
        if len(valor) < 2:
            raise ValueError("Informe um nome com pelo menos 2 letras")
        return valor

    @field_validator("email")
    @classmethod
    def validar_email(cls, valor: str) -> str:
        valor = valor.strip().lower()
        usuario, _, dominio = valor.partition("@")
        if not usuario or "." not in dominio or " " in valor:
            raise ValueError("E-mail inválido")
        return valor


class UsuarioLogin(BaseModel):
    email: str
    senha: str

    @field_validator("email")
    @classmethod
    def normalizar(cls, valor: str) -> str:
        return valor.strip().lower()


class UsuarioResponse(BaseModel):
    id: int
    nome: str
    email: str
    perfil_preenchido: bool = False

    model_config = ConfigDict(from_attributes=True)


class UsuarioLogado(UsuarioResponse):
    """Resposta do cadastro e do login: os dados do usuário + o token de acesso."""

    token: str
    # Só no cadastro e na recuperação de senha: a tela mostra uma vez e não guarda
    codigo_recuperacao: Optional[str] = None


class RecuperarSenha(BaseModel):
    email: str
    codigo: str = Field(min_length=1, max_length=40)
    nova_senha: str = Field(min_length=6, max_length=128)

    @field_validator("email")
    @classmethod
    def normalizar(cls, valor: str) -> str:
        return valor.strip().lower()


class CodigoRecuperacao(BaseModel):
    codigo_recuperacao: str
