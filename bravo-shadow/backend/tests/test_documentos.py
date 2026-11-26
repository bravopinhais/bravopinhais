import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.modules.categorias.schemas import CategoriaInput

from app.main import app, create_app


client = TestClient(app)


def setup_function():
    app.state.services.documentos._items.clear()
    app.state.services.categorias._items.clear()


def payload(**overrides):
    data = {
        "pasta": "Financeiro",
        "titulo": "Ata de reunião",
        "nomeArquivo": "ata.pdf",
        "arquivoCompactadoGzip": "H4sIAAAAA",
    }
    data.update(overrides)
    return data


def test_document_crud_preserves_file_payload_and_original_name():
    created = client.post("/api/v1/documentos", json=payload())
    assert created.status_code == 201
    item = created.json()
    assert item["nomeArquivo"] == "ata.pdf"
    assert item["arquivoCompactadoGzip"] == "H4sIAAAAA"
    assert client.get("/api/v1/documentos/" + item["id"]).status_code == 200
    changed = client.put(
        "/api/v1/documentos/" + item["id"],
        json=payload(titulo="Ata atualizada"),
    )
    assert changed.status_code == 200 and changed.json()["titulo"] == "Ata atualizada"
    assert client.delete("/api/v1/documentos/" + item["id"]).status_code == 204


def test_document_not_found():
    assert client.get("/api/v1/documentos/inexistente").status_code == 404
    assert client.delete("/api/v1/documentos/inexistente").status_code == 404


def test_document_requires_file_content():
    data = payload()
    data["arquivoCompactadoGzip"] = ""
    assert client.post("/api/v1/documentos", json=data).status_code == 422


def test_documents_are_isolated_between_app_instances():
    first = TestClient(create_app())
    second = TestClient(create_app())

    created = first.post("/api/v1/documentos", json=payload()).json()
    assert first.get("/api/v1/documentos/" + created["id"]).status_code == 200
    assert second.get("/api/v1/documentos").json() == []
    assert second.get("/api/v1/documentos/" + created["id"]).status_code == 404


def test_document_category_link_and_restrict_delete():
    category = app.state.services.categorias.create(CategoriaInput(nome="Atas"))
    created = client.post(
        "/api/v1/documentos",
        json=payload(categoriaId=category.id, pasta="Nome antigo"),
    )
    assert created.status_code == 201
    document = created.json()
    assert document["categoriaId"] == category.id
    assert document["pasta"] == "Atas"
    with pytest.raises(HTTPException) as error:
        app.state.services.categorias.delete(category.id)
    assert error.value.status_code == 409
    assert client.delete("/api/v1/documentos/" + document["id"]).status_code == 204
    app.state.services.categorias.delete(category.id)
def test_document_rejects_unknown_category():
    response = client.post(
        "/api/v1/documentos",
        json=payload(categoriaId="categoria-inexistente"),
    )
    assert response.status_code == 404


def test_document_metadata_is_trimmed_and_compressed_content_is_preserved():
    compressed_payload = "  H4sIAAAAA==  "
    response = client.post(
        "/api/v1/documentos",
        json=payload(
            pasta="  Financeiro  ",
            categoriaId="  ",
            titulo="  Ata de reunião  ",
            nomeArquivo="  ata final.pdf  ",
            arquivoCompactadoGzip=compressed_payload,
        ),
    )
    assert response.status_code == 201
    item = response.json()
    assert item["pasta"] == "Financeiro"
    assert item["categoriaId"] is None
    assert item["titulo"] == "Ata de reunião"
    assert item["nomeArquivo"] == "ata final.pdf"
    assert item["arquivoCompactadoGzip"] == compressed_payload


def test_document_required_metadata_rejects_whitespace_only():
    assert client.post("/api/v1/documentos", json=payload(titulo="   ")).status_code == 422
    assert client.post("/api/v1/documentos", json=payload(nomeArquivo="   ")).status_code == 422


def test_document_category_id_is_trimmed_before_lookup():
    category = app.state.services.categorias.create(CategoriaInput(nome="Atas"))
    response = client.post(
        "/api/v1/documentos",
        json=payload(categoriaId=f"  {category.id}  "),
    )
    assert response.status_code == 201
    assert response.json()["categoriaId"] == category.id
    assert response.json()["pasta"] == "Atas"
