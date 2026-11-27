from app.core.postgres_usuarios import PostgresUsuariosRepository
from app.core.storage import build_storage_services
from app.modules.usuarios.schemas import Usuario


class Cursor:
    def __init__(self, connection):
        self.connection = connection
        self.rowcount = connection.rowcount

    def execute(self, sql, params=()):
        self.connection.calls.append((sql, params))
        if sql.lstrip().startswith("SELECT") or "RETURNING" in sql:
            self.connection.row = self.connection.row_value

    def fetchone(self):
        return self.connection.row

    def fetchall(self):
        return self.connection.rows

    def close(self):
        self.connection.cursor_closed += 1


class Connection:
    def __init__(self, *, row=None, rows=None, rowcount=1):
        self.row_value = row
        self.row = None
        self.rows = rows or []
        self.rowcount = rowcount
        self.calls = []
        self.commits = 0
        self.rollbacks = 0
        self.closed = 0
        self.cursor_closed = 0

    def cursor(self):
        return Cursor(self)

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.closed += 1


def factory(connection):
    return lambda: connection


def test_user_repository_reads_admin_but_generic_insert_is_cadastral_only():
    import pytest

    row = ("usr_1", "person@example.com", "Pessoa", "Bravo", "Operador", "Admin", "Ativo")
    connection = Connection(row=row)
    repository = PostgresUsuariosRepository(factory(connection))

    item = repository.get("usr_1")

    assert item == Usuario(
        id="usr_1", email="person@example.com", nome="Pessoa",
        loja="Bravo", cargo="Operador", perfil="Admin", status="Ativo",
    )
    # A identidade Google ainda não é persistida: não deve aparecer
    # no SELECT/INSERT nem existir operação de vínculo neste estágio.
    assert "google_subject" not in repository._columns.lower()
    assert not hasattr(repository, "link_google_subject")
    assert "google_subject" not in connection.calls[0][0].lower()

    with pytest.raises(ValueError, match="somente Operador/Ativo"):
        repository.add("usr_2", item)
    assert len(connection.calls) == 1
    assert connection.commits == 1


def test_postgres_generic_insert_forces_only_cadastral_profile():
    connection = Connection()
    repository = PostgresUsuariosRepository(factory(connection))
    item = Usuario(
        id="usr_2", email="person@example.com", nome="Pessoa",
        loja="Bravo", cargo="Operador", perfil="Operador", status="Ativo",
    )

    repository.add("usr_2", item)

    assert connection.calls[0][1] == (
        "usr_2", "person@example.com", "Pessoa", "Bravo", "Operador", "Operador", "Ativo"
    )
    assert "google_subject" not in connection.calls[0][0].lower()
    assert "senha" not in connection.calls[0][0].lower()
    assert connection.commits == 1


def test_postgres_generic_replace_is_blocked_before_opening_connection():
    import pytest

    connection = Connection()
    repository = PostgresUsuariosRepository(factory(connection))
    item = Usuario(
        id="usr_1", email="person@example.com", nome="Pessoa",
        loja="Bravo", cargo="Operador", perfil="Admin", status="Ativo",
    )

    with pytest.raises(RuntimeError, match="Substituição genérica"):
        repository.replace("usr_1", item)

    assert connection.calls == []
    assert connection.commits == 0


def test_postgres_storage_wires_user_profiles_without_connecting():
    def unexpected_connection():
        raise AssertionError("A conexão não deve abrir durante a montagem.")

    services = build_storage_services("postgres", connection_factory=unexpected_connection)

    assert isinstance(services.usuarios.repository, PostgresUsuariosRepository)



class UniqueViolation(Exception):
    sqlstate = "23505"

    def __init__(self, constraint_name):
        self.diag = type("Diagnostic", (), {"constraint_name": constraint_name})()


class FailingCursor(Cursor):
    def __init__(self, connection, error):
        super().__init__(connection)
        self.error = error

    def execute(self, sql, params=()):
        self.connection.calls.append((sql, params))
        raise self.error


class FailingConnection(Connection):
    def __init__(self, error):
        super().__init__()
        self.error = error

    def cursor(self):
        return FailingCursor(self, self.error)


def test_postgres_translates_only_email_unique_constraint_to_conflict():
    from fastapi import HTTPException
    import pytest

    connection = FailingConnection(UniqueViolation("usuarios_email_ci_uidx"))
    repository = PostgresUsuariosRepository(factory(connection))

    with pytest.raises(HTTPException) as error:
        repository.add("usr_2", Usuario(
            id="usr_2", email="person@example.com", nome="Pessoa",
            loja="Bravo", cargo="Conselho", perfil="Operador", status="Ativo",
        ))

    assert error.value.status_code == 409
    assert connection.rollbacks == 1
    assert connection.closed == 1


def test_postgres_does_not_mask_other_unique_constraint_violations():
    import pytest

    error = UniqueViolation("usuarios_pkey")
    connection = FailingConnection(error)
    repository = PostgresUsuariosRepository(factory(connection))

    with pytest.raises(UniqueViolation) as raised:
        repository.add("usr_2", Usuario(
            id="usr_2", email="person@example.com", nome="Pessoa",
            loja="Bravo", cargo="Conselho", perfil="Operador", status="Ativo",
        ))

    assert raised.value is error
    assert connection.rollbacks == 1
    assert connection.closed == 1



class CloseFailingCursor(FailingCursor):
    def close(self):
        raise RuntimeError("cursor close failed")


class CloseFailingConnection(FailingConnection):
    def cursor(self):
        return CloseFailingCursor(self, self.error)


def test_repository_preserves_query_error_when_cursor_close_also_fails():
    import pytest

    original_error = UniqueViolation("usuarios_pkey")
    connection = CloseFailingConnection(original_error)
    repository = PostgresUsuariosRepository(factory(connection))

    with pytest.raises(UniqueViolation) as raised:
        repository.add("usr_2", Usuario(
            id="usr_2", email="person@example.com", nome="Pessoa",
            loja="Bravo", cargo="Conselho", perfil="Operador", status="Ativo",
        ))

    assert raised.value is original_error
    assert any("fechamento do cursor" in note for note in getattr(original_error, "__notes__", ()))
    assert connection.rollbacks == 1
    assert connection.closed == 1


def test_postgres_user_repository_blocks_physical_delete_without_opening_connection():
    import pytest
    from fastapi import HTTPException

    def unexpected_connection():
        raise AssertionError("Exclusão física não deve abrir conexão.")

    repository = PostgresUsuariosRepository(unexpected_connection)
    with pytest.raises(HTTPException) as error:
        repository.delete("usr_1")

    assert error.value.status_code == 410



def test_postgres_cadastral_update_never_writes_profile_or_status():
    row = ("usr_1", "person@example.com", "Nome atualizado", "Bravo", "Conselho", "Admin", "Inativo")
    connection = Connection(row=row)
    repository = PostgresUsuariosRepository(factory(connection))

    updated = repository.update_cadastral("usr_1", nome="Nome atualizado")

    sql, params = connection.calls[0]
    normalized_sql = " ".join(sql.lower().split())
    assert "set nome = %s" in normalized_sql
    assert "perfil =" not in normalized_sql
    assert "status =" not in normalized_sql
    assert "returning id, email, nome, loja, cargo, perfil, status" in normalized_sql
    assert params == ("Nome atualizado", "usr_1")
    assert updated.perfil == "Admin"
    assert updated.status == "Inativo"
    assert connection.commits == 1


def test_postgres_cadastral_update_rejects_empty_payload_without_connection():
    import pytest

    def unexpected_connection():
        raise AssertionError("Payload vazio não deve abrir conexão.")

    repository = PostgresUsuariosRepository(unexpected_connection)
    with pytest.raises(ValueError):
        repository.update_cadastral("usr_1")
