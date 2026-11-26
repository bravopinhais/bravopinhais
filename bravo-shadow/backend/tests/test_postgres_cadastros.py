from decimal import Decimal

from app.core.postgres_cadastros import (
    PostgresContasBancariasRepository,
    PostgresEmpregadosRepository,
    PostgresFornecedoresRepository,
    PostgresMoradoresRepository,
)
from app.modules.contas_bancarias.schemas import ContaBancaria
from app.modules.empregados.schemas import Empregado
from app.modules.fornecedores.schemas import Fornecedor
from app.modules.moradores.schemas import Morador


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


def test_moradores_repository_maps_sensitive_and_optional_fields():
    connection = Connection(row=(
        "mor_1", "A", "101", "Ana", "ana@example.test",
        "11999990000", "00000000000", "Luna", "12",
    ))
    repository = PostgresMoradoresRepository(factory(connection))

    item = repository.get("mor_1")

    assert item == Morador(
        id="mor_1", bloco="A", apartamento="101", nome="Ana",
        email="ana@example.test", telefone="11999990000",
        cpf="00000000000", petNome="Luna", vagaGaragem="12",
    )
    assert "cpf" in connection.calls[0][0]
    assert connection.commits == 1


def test_fornecedores_repository_inserts_and_updates_legacy_fields():
    connection = Connection()
    repository = PostgresFornecedoresRepository(factory(connection))
    item = Fornecedor(id="for_1", cnpj="00000000000100", razaoSocial="Fornecedor Ltda")

    repository.add(item.id, item)
    repository.replace(item.id, item)

    assert connection.calls[0][1] == ("for_1", "00000000000100", "Fornecedor Ltda")
    assert "razao_social = %s" in connection.calls[1][0]
    assert connection.commits == 2


def test_empregados_repository_preserves_emergency_contact_fields():
    connection = Connection(row=(
        "emp_1", "Carlos", "Zelador", "Condomínio", "Rua A",
        "11988887777", "Maria", "11977776666",
    ))
    repository = PostgresEmpregadosRepository(factory(connection))

    item = repository.get("emp_1")

    assert item == Empregado(
        id="emp_1", nome="Carlos", cargo="Zelador", empresa="Condomínio",
        endereco="Rua A", telefone="11988887777",
        contatoEmergenciaNome="Maria", contatoEmergenciaTel="11977776666",
    )


def test_bank_accounts_repository_preserves_reported_balance():
    connection = Connection(row=("cb_1", "Banco Exemplo", Decimal("1234.56")))
    repository = PostgresContasBancariasRepository(factory(connection))

    item = repository.get("cb_1")

    assert item == ContaBancaria(id="cb_1", banco="Banco Exemplo", saldo=Decimal("1234.56"))
    assert "saldo" in connection.calls[0][0]


def test_postgres_storage_wires_all_four_cadastro_repositories_without_connecting():
    from app.core.storage import build_storage_services

    def unexpected_connection():
        raise AssertionError("A conexão não deve ser aberta ao montar os serviços.")

    services = build_storage_services("postgres", connection_factory=unexpected_connection)

    assert isinstance(services.moradores.repository, PostgresMoradoresRepository)
    assert isinstance(services.fornecedores.repository, PostgresFornecedoresRepository)
    assert isinstance(services.empregados.repository, PostgresEmpregadosRepository)
    assert isinstance(services.contas_bancarias.repository, PostgresContasBancariasRepository)
