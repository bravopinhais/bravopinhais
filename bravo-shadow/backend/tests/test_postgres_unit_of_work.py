from app.core.postgres import (
    CommitOutcomeUnknown,
    CommitSucceededCleanupError,
    PostgresUnitOfWork,
)


class FakeConnection:
    def __init__(self, commit_error=None):
        self.commits = 0
        self.rollbacks = 0
        self.closes = 0
        self.commit_error = commit_error

    def commit(self):
        self.commits += 1
        if self.commit_error:
            raise self.commit_error

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.closes += 1


def test_unit_of_work_commits_and_closes_on_success():
    connection = FakeConnection()
    with PostgresUnitOfWork(lambda: connection) as work:
        assert work.connection is connection
    assert connection.commits == 1
    assert connection.rollbacks == 0
    assert connection.closes == 1
    assert work.connection is None


def test_unit_of_work_rolls_back_and_closes_on_error():
    connection = FakeConnection()
    try:
        with PostgresUnitOfWork(lambda: connection):
            raise RuntimeError("falha simulada")
    except RuntimeError:
        pass
    else:
        raise AssertionError("A exceção deveria ser propagada")
    assert connection.commits == 0
    assert connection.rollbacks == 1
    assert connection.closes == 1


def test_unit_of_work_rolls_back_if_commit_fails_and_still_closes():
    connection = FakeConnection(commit_error=RuntimeError("commit falhou"))
    try:
        with PostgresUnitOfWork(lambda: connection):
            pass
    except CommitOutcomeUnknown as error:
        assert str(error) == "postgres_commit_outcome_unknown"
        assert isinstance(error.__cause__, RuntimeError)
        assert str(error.__cause__) == "commit falhou"
    else:
        raise AssertionError("A falha do commit deveria ser propagada")
    assert connection.commits == 1
    assert connection.rollbacks == 1
    assert connection.closes == 1

class RollbackFailConnection(FakeConnection):
    def rollback(self):
        self.rollbacks += 1
        raise RuntimeError("rollback falhou")


def test_unit_of_work_preserves_body_error_when_rollback_fails():
    connection = RollbackFailConnection()
    try:
        with PostgresUnitOfWork(lambda: connection):
            raise ValueError("erro original")
    except ValueError as error:
        assert str(error) == "erro original"
        assert any("rollback" in note for note in error.__notes__)
    else:
        raise AssertionError("A exceção original deveria ser propagada")
    assert connection.commits == 0
    assert connection.rollbacks == 1
    assert connection.closes == 1


def test_unit_of_work_preserves_commit_error_when_rollback_fails():
    connection = RollbackFailConnection(commit_error=RuntimeError("commit falhou"))
    try:
        with PostgresUnitOfWork(lambda: connection):
            pass
    except CommitOutcomeUnknown as error:
        assert str(error) == "postgres_commit_outcome_unknown"
        assert isinstance(error.__cause__, RuntimeError)
        assert any("rollback" in note for note in error.__notes__)
    else:
        raise AssertionError("A falha original do commit deveria ser propagada")
    assert connection.commits == 1
    assert connection.rollbacks == 1
    assert connection.closes == 1


class CloseFailConnection(FakeConnection):
    def close(self):
        self.closes += 1
        raise RuntimeError("close falhou")


def test_unit_of_work_preserves_body_error_when_connection_close_fails():
    connection = CloseFailConnection()
    try:
        with PostgresUnitOfWork(lambda: connection):
            raise ValueError("erro original")
    except ValueError as error:
        assert str(error) == "erro original"
        assert any("fechamento" in note for note in error.__notes__)
    else:
        raise AssertionError("A exceção original deveria ser propagada")
    assert connection.rollbacks == 1
    assert connection.closes == 1


def test_unit_of_work_preserves_commit_error_when_connection_close_fails():
    connection = CloseFailConnection(commit_error=RuntimeError("commit falhou"))
    try:
        with PostgresUnitOfWork(lambda: connection):
            pass
    except CommitOutcomeUnknown as error:
        assert str(error) == "postgres_commit_outcome_unknown"
        assert isinstance(error.__cause__, RuntimeError)
        assert any("fechamento" in note for note in error.__notes__)
    else:
        raise AssertionError("A falha original do commit deveria ser propagada")
    assert connection.rollbacks == 1
    assert connection.closes == 1


def test_unit_of_work_propagates_close_error_after_successful_commit():
    connection = CloseFailConnection()
    try:
        with PostgresUnitOfWork(lambda: connection):
            pass
    except CommitSucceededCleanupError as error:
        assert str(error) == "postgres_commit_succeeded_connection_close_failed"
        assert isinstance(error.__cause__, RuntimeError)
        assert str(error.__cause__) == "close falhou"
    else:
        raise AssertionError("A falha de fechamento deveria ser classificada após commit")
    assert connection.commits == 1
    assert connection.rollbacks == 0
    assert connection.closes == 1


def test_unit_of_work_rejects_non_callable_connection_factory():
    for factory in (None, object(), "not-callable"):
        try:
            PostgresUnitOfWork(factory)
        except TypeError as error:
            assert "connection_factory" in str(error)
        else:
            raise AssertionError("A fábrica inválida deveria ser rejeitada")


def test_unit_of_work_propagates_connection_factory_error():
    expected_error = RuntimeError("falha ao abrir conexão")

    def failing_factory():
        raise expected_error

    work = PostgresUnitOfWork(failing_factory)
    try:
        work.__enter__()
    except RuntimeError as error:
        assert error is expected_error
    else:
        raise AssertionError("A falha da fábrica deveria ser propagada")

    assert work.connection is None


def test_unit_of_work_rejects_invalid_connection_returned_by_factory():
    for invalid_connection in (None, object(), {"commit": "not-callable"}):
        work = PostgresUnitOfWork(lambda: invalid_connection)
        try:
            work.__enter__()
        except TypeError as error:
            assert "commit, rollback e close" in str(error)
        else:
            raise AssertionError("A conexão inválida deveria ser rejeitada")
        assert work.connection is None


class InvalidConnectionWithClose:
    def __init__(self):
        self.closes = 0

    def close(self):
        self.closes += 1


def test_unit_of_work_closes_invalid_connection_when_close_is_available():
    connection = InvalidConnectionWithClose()
    work = PostgresUnitOfWork(lambda: connection)

    try:
        work.__enter__()
    except TypeError as error:
        assert "commit, rollback e close" in str(error)
    else:
        raise AssertionError("A conexão incompleta deveria ser rejeitada")

    assert connection.closes == 1
    assert work.connection is None

class InvalidConnectionCloseFails:
    def close(self):
        raise RuntimeError("close falhou")


def test_unit_of_work_preserves_invalid_connection_error_if_close_fails():
    connection = InvalidConnectionCloseFails()
    work = PostgresUnitOfWork(lambda: connection)

    try:
        work.__enter__()
    except TypeError as error:
        assert "commit, rollback e close" in str(error)
    else:
        raise AssertionError("A conexão incompleta deveria ser rejeitada")

    assert work.connection is None

