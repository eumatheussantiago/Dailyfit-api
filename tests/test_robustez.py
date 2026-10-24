from sqlalchemy.exc import OperationalError

import database


def test_site_sobe_com_o_banco_fora_do_ar(monkeypatch, caplog):
    def banco_fora(*args, **kwargs):
        raise OperationalError("SELECT 1", {}, Exception("conexão recusada"))

    monkeypatch.setattr(database, "_criar_tabelas", banco_fora)
    database.criar_tabelas()  # não pode derrubar o app na largada
    assert "Banco indisponível" in caplog.text
