from fastapi.testclient import TestClient
from app.main import app
from app.modules.estoque.service import estoque_service
from app.modules.acertos_estoque.service import acertos_estoque_service

client = TestClient(app)

def setup_function():
    estoque_service._items.clear()
    acertos_estoque_service._items.clear()

def test_stock_crud_and_extended_origin_fields():
    response = client.post('/api/v1/estoque', json={'item':'Lâmpada LED','quantidade':5,'minimo':2,'maximo':10,'etiqueta':'789','marca':'Marca A','linha':'LED','fabricante':'Fábrica X','dataCadastro':'2026-11-26'})
    assert response.status_code == 201
    item = response.json()
    assert item['marca'] == 'Marca A' and item['fabricante'] == 'Fábrica X'
    assert client.put('/api/v1/estoque/'+item['id'], json={'item':'Lâmpada LED 9W','quantidade':4,'minimo':2,'maximo':10,'etiqueta':'789'}).status_code == 200
    assert client.delete('/api/v1/estoque/'+item['id']).status_code == 204

def test_adjustment_updates_quantity_and_prevents_negative_balance():
    product = client.post('/api/v1/estoque', json={'item':'Cabo','quantidade':5}).json()
    move = client.post('/api/v1/acertos-estoque', json={'tipo':'Saída','produtoId':product['id'],'quantidade':2,'motivo':'Uso interno'})
    assert move.status_code == 201
    assert client.get('/api/v1/estoque').json()[0]['quantidade'] == 3
    assert client.post('/api/v1/acertos-estoque', json={'tipo':'Saída','produtoId':product['id'],'quantidade':4,'motivo':'Uso'}).status_code == 409
    assert client.delete('/api/v1/acertos-estoque/'+move.json()['id']).status_code == 204
    assert client.get('/api/v1/estoque').json()[0]['quantidade'] == 3

def test_adjustment_requires_existing_product():
    assert client.post('/api/v1/acertos-estoque', json={'tipo':'Entrada','produtoId':'missing','quantidade':1,'motivo':'Teste'}).status_code == 404
