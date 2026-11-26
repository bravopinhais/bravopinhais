from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.core.storage import configure_storage
from app.main import create_app


class FakePostgresState:
    def __init__(self):
        self.plan_accounts = {}
        self.financial_titles = {}


class FakeCursor:
    def __init__(self, connection):
        self.connection = connection
        self.rows = []
        self.rowcount = 0

    def execute(self, sql, params=()):
        state = self.connection.state
        self.connection.statements.append((sql, params))
        self.rows = []
        self.rowcount = 0

        if sql.startswith("SELECT id, codigo, nome, tipo, version FROM bravo_shadow.plano_contas"):
            if "WHERE id = %s" in sql:
                item = state.plan_accounts.get(params[0])
                self.rows = [tuple(item.values())] if item else []
            else:
                self.rows = [
                    (item["id"], item["codigo"], item["nome"], item["tipo"], item["version"])
                    for item in sorted(state.plan_accounts.values(), key=lambda row: row["codigo"])
                ]
            return

        if sql.startswith("SELECT id, tipo, plano_conta_id, historico, valor, version FROM bravo_shadow.financeiro"):
            if "WHERE id = %s" in sql:
                item = state.financial_titles.get(params[0])
                self.rows = [self._finance_row(item)] if item else []
            else:
                self.rows = [
                    self._finance_row(item)
                    for item in sorted(state.financial_titles.values(), key=lambda row: row["id"])
                ]
            return

        if sql.startswith("SELECT 1 FROM bravo_shadow.financeiro"):
            self.rows = [(1,)] if any(
                row["plano_conta_id"] == params[0]
                for row in state.financial_titles.values()
            ) else []
            return

        if sql.startswith("SELECT version FROM bravo_shadow."):
            table = state.plan_accounts if "plano_contas" in sql else state.financial_titles
            item = table.get(params[0])
            self.rows = [(item["version"],)] if item else []
            return

        if sql.startswith("INSERT INTO bravo_shadow.plano_contas"):
            item_id, codigo, nome, tipo = params
            if any(row["codigo"].casefold() == codigo.casefold() for row in state.plan_accounts.values()):
                raise self._db_error("23505")
            state.plan_accounts[item_id] = {
                "id": item_id, "codigo": codigo, "nome": nome, "tipo": tipo, "version": 1,
            }
            self.rowcount = 1
            return

        if sql.startswith("INSERT INTO bravo_shadow.financeiro"):
            item_id, tipo, account_id, historico, amount = params
            if account_id is not None and account_id not in state.plan_accounts:
                raise self._db_error("23503")
            state.financial_titles[item_id] = {
                "id": item_id, "tipo": tipo, "plano_conta_id": account_id,
                "historico": historico, "valor": Decimal(amount), "version": 1,
            }
            self.rowcount = 1
            return

        if sql.startswith("UPDATE bravo_shadow.plano_contas SET"):
            codigo, nome, tipo, item_id, expected = params
            item = state.plan_accounts.get(item_id)
            if item and item["version"] == expected:
                if any(row["id"] != item_id and row["codigo"].casefold() == codigo.casefold()
                       for row in state.plan_accounts.values()):
                    raise self._db_error("23505")
                item.update(codigo=codigo, nome=nome, tipo=tipo, version=expected + 1)
                self.rowcount = 1
            return

        if sql.startswith("UPDATE bravo_shadow.financeiro SET"):
            tipo, account_id, historico, amount, item_id, expected = params
            item = state.financial_titles.get(item_id)
            if item and item["version"] == expected:
                if account_id is not None and account_id not in state.plan_accounts:
                    raise self._db_error("23503")
                item.update(
                    tipo=tipo, plano_conta_id=account_id, historico=historico,
                    valor=Decimal(amount), version=expected + 1,
                )
                self.rowcount = 1
            return

        if sql.startswith("DELETE FROM bravo_shadow.plano_contas"):
            item_id = params[0]
            if any(row["plano_conta_id"] == item_id for row in state.financial_titles.values()):
                raise self._db_error("23503")
            self.rowcount = int(state.plan_accounts.pop(item_id, None) is not None)
            return

        if sql.startswith("DELETE FROM bravo_shadow.financeiro"):
            self.rowcount = int(state.financial_titles.pop(params[0], None) is not None)
            return

        raise AssertionError(f"SQL não previsto no teste: {sql}")

    @staticmethod
    def _finance_row(item):
        return (
            item["id"], item["tipo"], item["plano_conta_id"], item["historico"],
            item["valor"], item["version"],
        )

    @staticmethod
    def _db_error(sqlstate):
        error = RuntimeError(f"Simulação de erro PostgreSQL {sqlstate}")
        error.sqlstate = sqlstate
        return error

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def fetchall(self):
        return list(self.rows)

    def close(self):
        self.connection.cursors_closed += 1


class FakeConnection:
    def __init__(self, state):
        self.state = state
        self.statements = []
        self.commits = 0
        self.rollbacks = 0
        self.closed = 0
        self.cursors_closed = 0

    def cursor(self):
        return FakeCursor(self)

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.closed += 1


@pytest.fixture
def postgres_api():
    state = FakePostgresState()
    connections = []

    def connection_factory():
        connection = FakeConnection(state)
        connections.append(connection)
        return connection

    application = create_app(
        storage_backend="postgres",
        postgres_connection_factory=connection_factory,
    )
    try:
        with TestClient(application) as client:
            yield client, state, connections
    finally:
        configure_storage("memory")


def test_postgres_routes_create_read_update_and_enforce_references(postgres_api):
    client, state, connections = postgres_api

    account_response = client.post(
        "/api/v1/plano-contas",
        json={"codigo": "1.1", "nome": "Receita ordinária", "tipo": "Receita"},
    )
    assert account_response.status_code == 201
    account = account_response.json()
    assert account_response.headers["etag"] == '"1"'

    title_response = client.post(
        "/api/v1/financeiro",
        json={
            "tipo": "Receber", "planoContaId": account["id"],
            "historico": "Cota mensal", "valor": "350.75",
        },
    )
    assert title_response.status_code == 201
    title = title_response.json()
    assert title["planoContaId"] == account["id"]
    assert title_response.headers["etag"] == '"1"'

    assert client.get("/api/v1/plano-contas").json()[0]["id"] == account["id"]
    assert client.get("/api/v1/financeiro").json()[0]["valor"] == 350.75

    updated_account = client.put(
        f"/api/v1/plano-contas/{account['id']}",
        json={"codigo": "1.1", "nome": "Receita atualizada", "tipo": "Receita"},
        headers={"If-Match": '"1"'},
    )
    assert updated_account.status_code == 200
    assert updated_account.json()["version"] == 2
    assert updated_account.headers["etag"] == '"2"'

    updated_title = client.put(
        f"/api/v1/financeiro/{title['id']}",
        json={
            "tipo": "Receber", "planoContaId": account["id"],
            "historico": "Cota revisada", "valor": "375.00",
        },
        headers={"If-Match": '"1"'},
    )
    assert updated_title.status_code == 200
    assert updated_title.json()["version"] == 2
    assert updated_title.headers["etag"] == '"2"'

    stale = client.put(
        f"/api/v1/financeiro/{title['id']}",
        json={
            "tipo": "Receber", "planoContaId": account["id"],
            "historico": "Edição obsoleta", "valor": "1.00",
        },
        headers={"If-Match": '"1"'},
    )
    assert stale.status_code == 409
    assert state.financial_titles[title["id"]]["historico"] == "Cota revisada"

    blocked_delete = client.delete(f"/api/v1/plano-contas/{account['id']}")
    assert blocked_delete.status_code == 409
    assert account["id"] in state.plan_accounts

    assert client.delete(f"/api/v1/financeiro/{title['id']}").status_code == 204
    assert client.delete(f"/api/v1/plano-contas/{account['id']}").status_code == 204
    assert state.financial_titles == {}
    assert state.plan_accounts == {}
    assert connections
    assert all(connection.closed == connection.cursors_closed for connection in connections)


def test_postgres_routes_reject_duplicate_account_code(postgres_api):
    client, _state, _connections = postgres_api
    first = client.post(
        "/api/v1/plano-contas",
        json={"codigo": "2.1", "nome": "Receita A", "tipo": "Receita"},
    )
    assert first.status_code == 201

    duplicate = client.post(
        "/api/v1/plano-contas",
        json={"codigo": "2.1", "nome": "Receita B", "tipo": "Receita"},
    )
    assert duplicate.status_code == 409
