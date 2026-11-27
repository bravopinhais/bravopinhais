from app.core.postgres_usuarios import PostgresUsuariosRepository
from app.core.storage import build_storage_services
from app.modules.usuarios.schemas import Usuario


class Cursor:
    def __init__(self, connection):
        self.connection = connection
        self.rowcount = connection.rowcount

    def execute(self, sql, params=()):
        self.connection.calls.append((sql, params))
        if sql.lstrip().startswith("SELECT"):
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


def test_user_repository_maps_and_persists_google_email_profile_only():
    row = ("usr_1", "person@example.com", "Pessoa", "Bravo", "Operador", "Admin", "Ativo")
    connection = Connection(row=row)
    repository = PostgresUsuariosRepository(factory(connection))

    item = repository.get("usr_1")

    assert item == Usuario(
        id="usr_1", email="person@example.com", nome="Pessoa",
        loja="Bravo", cargo="Operador", perfil="Admin", status="Ativo",
    )
    repository.add("usr_2", item)
    assert connection.calls[1][1] == (
        "usr_2", "person@example.com", "Pessoa", "Bravo", "Operador", "Admin", "Ativo"
    )
    assert "senha" not in connection.calls[1][0].lower()
    assert connection.commits == 2


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
    assert any("fechamento do cursor" in note for note in original_error.__notes__)
    assert connection.rollbacks == 1
    assert connection.closed == 1
