import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# Padrão: arquivo SQLite criado automaticamente na pasta do projeto.
# Em produção (Render), a variável de ambiente DATABASE_URL aponta para o
# PostgreSQL do Supabase — não é preciso mudar o código.
BASE_DIR = Path(__file__).resolve().parent


def montar_url(url: str) -> str:
    """Usa o driver psycopg 3 para PostgreSQL, qualquer que seja o formato da URL."""
    for prefixo in ("postgres://", "postgresql://"):
        if url.startswith(prefixo):
            return "postgresql+psycopg://" + url[len(prefixo):]
    return url


DATABASE_URL = montar_url(
    os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'dailyfit.db'}")
)
USANDO_SQLITE = DATABASE_URL.startswith("sqlite")

if USANDO_SQLITE:
    # "check_same_thread" só existe no SQLite
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,   # reconecta sozinho se a conexão cair (ex.: servidor dormiu)
        pool_recycle=300,
        pool_size=3,          # o plano grátis do Supabase limita as conexões
        max_overflow=2,
    )

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


def agora_utc() -> datetime:
    """Data e hora atuais em UTC (sem fuso), o padrão salvo no banco.

    O servidor do Render roda em UTC e o computador de cada um no horário local;
    salvar sempre em UTC evita o horário "pular" 3 horas. A API devolve a data
    com o fuso (Z) e o navegador converte para o horário de quem está usando.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


def criar_tabelas():
    """Cria as tabelas que faltam e adiciona colunas novas em bancos já existentes.

    Assim, quem já tinha um dailyfit.db de uma versão anterior não precisa
    apagar o arquivo quando o projeto ganha um campo novo (ex.: senha).
    Se o banco estiver fora do ar, avisa no log e deixa o site subir (as páginas
    abrem; a API responde erro até o banco voltar).
    """
    try:
        _criar_tabelas()
    except OperationalError as erro:
        logging.getLogger(__name__).error("Banco indisponível ao iniciar; tabelas não conferidas: %s", erro.__class__.__name__)


def _criar_tabelas():
    Base.metadata.create_all(bind=engine)

    inspetor = inspect(engine)
    with engine.begin() as conexao:
        for tabela in Base.metadata.sorted_tables:
            existentes = {coluna["name"] for coluna in inspetor.get_columns(tabela.name)}
            for coluna in tabela.columns:
                if coluna.name not in existentes and coluna.nullable:
                    tipo = coluna.type.compile(dialect=engine.dialect)
                    conexao.execute(
                        text(f'ALTER TABLE {tabela.name} ADD COLUMN "{coluna.name}" {tipo}')
                    )

            # No Supabase, as tabelas também ficam visíveis pela API pública dele.
            # Ligar o RLS (sem regras) bloqueia esse acesso; o app continua
            # funcionando porque é o dono das tabelas.
            if engine.dialect.name == "postgresql":
                conexao.execute(text(f"ALTER TABLE {tabela.name} ENABLE ROW LEVEL SECURITY"))

            # create_all não cria índices novos em tabelas que já existem
            for indice in tabela.indexes:
                indice.create(bind=conexao, checkfirst=True)


def get_db():
    """Abre uma sessão por requisição e garante que ela seja fechada no final."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
