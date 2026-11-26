from app.core.postgres import PostgresUnitOfWork


class FakeConnection:
    def __init__(self):
        self.commits = 0
        self.rollbacks = 0
        self.closes = 0

    def commit(self):
        self.commits += 1

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
