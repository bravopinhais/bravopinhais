from app.core.repositories import InMemoryCollectionRepository


def test_in_memory_repository_crud():
    repository = InMemoryCollectionRepository[str, str]()
    repository.add("a", "alpha")
    assert repository.exists("a")
    assert repository.get("a") == "alpha"
    assert repository.list() == ["alpha"]

    repository.replace("a", "updated")
    assert repository.get("a") == "updated"

    repository.delete("a")
    assert not repository.exists("a")
    assert repository.list() == []


def test_in_memory_repository_rejects_duplicate_add_and_missing_replace():
    repository = InMemoryCollectionRepository[str, str]()
    repository.add("a", "alpha")

    try:
        repository.add("a", "duplicate")
        assert False, "A inclusão duplicada deveria falhar."
    except KeyError:
        pass

    try:
        repository.replace("missing", "value")
        assert False, "A atualização de registro inexistente deveria falhar."
    except KeyError:
        pass
