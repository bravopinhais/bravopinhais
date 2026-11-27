from app.core.postgres import PostgresUnitOfWork


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
    except RuntimeError as error:
        assert str(error) == "commit falhou"
    else:
        raise AssertionError("A falha do commit deveria ser propagada")
    assert connection.commits == 1
    assert connection.rollbacks == 1
    assert connection.closes == 1

class RollbackFailConnection(FakeConnection):
    def rollback(self):
        self.rollbacks += 1
        raise RuntimeError("rollback falhou")


def test_unit_of_work_still_closes_when_rollback_fails_after_body_error():
    connection = RollbackFailConnection()
    try:
        with PostgresUnitOfWork(lambda: connection):
            raise ValueError("erro original")
    except RuntimeError as error:
        assert str(error) == "rollback falhou"
    else:
        raise AssertionError("A falha no rollback deveria ser propagada")
    assert connection.commits == 0
    assert connection.rollbacks == 1
    assert connection.closes == 1


def test_unit_of_work_still_closes_when_rollback_fails_after_commit_error():
    connection = RollbackFailConnection(commit_error=RuntimeError("commit falhou"))
    try:
        with PostgresUnitOfWork(lambda: connection):
            pass
    except RuntimeError as error:
        assert str(error) == "rollback falhou"
    else:
        raise AssertionError("A falha no rollback deveria ser propagada")
    assert connection.commits == 1
    assert connection.rollbacks == 1
    assert connection.closes == 1

