import os
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# Padrão: arquivo SQLite criado automaticamente na pasta do projeto.
# Para usar outro banco (ex.: MySQL ou PostgreSQL), defina a variável de
# ambiente DATABASE_URL — não é preciso mudar o código.
BASE_DIR = Path(__file__).resolve().parent
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'dailyfit.db'}")

# "check_same_thread" só existe no SQLite; os outros bancos não aceitam essa opção
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


def criar_tabelas():
    """Cria as tabelas que faltam e adiciona colunas novas em bancos já existentes.

    Assim, quem já tinha um dailyfit.db de uma versão anterior não precisa
    apagar o arquivo quando o projeto ganha um campo novo (ex.: senha).
    """
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


def get_db():
    """Abre uma sessão por requisição e garante que ela seja fechada no final."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
