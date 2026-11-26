from fastapi.testclient import TestClient
from app.main import app
from app.modules.categorias.service import categorias_service
from app.modules.motivos_acerto.service import motivos_acerto_service

client = TestClient(app)

def setup_function():
    categorias_service._items.clear()
    motivos_acerto_service._items.clear()

def test_categories_crud():
    created = client.post('/api/v1/categorias', json={'nome':'Financeiro'})
    assert created.status_code == 201
    item = created.json()
    assert client.get('/api/v1/categorias').json()[0]['nome'] == 'Financeiro'
    assert client.delete('/api/v1/categorias/'+item['id']).status_code == 204
    assert client.delete('/api/v1/categorias/'+item['id']).status_code == 404

def test_adjustment_reasons_crud():
    created = client.post('/api/v1/motivos-acerto-estoque', json={'nome':'Quebra'})
    assert created.status_code == 201
    item = created.json()
    assert client.get('/api/v1/motivos-acerto-estoque').json()[0]['nome'] == 'Quebra'
    assert client.delete('/api/v1/motivos-acerto-estoque/'+item['id']).status_code == 204

def test_names_are_required():
    assert client.post('/api/v1/categorias', json={'nome':''}).status_code == 422
    assert client.post('/api/v1/motivos-acerto-estoque', json={}).status_code == 422
