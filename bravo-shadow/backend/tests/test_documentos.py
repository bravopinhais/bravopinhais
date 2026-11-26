from fastapi.testclient import TestClient
from app.main import app
from app.modules.documentos.service import documentos_service

client = TestClient(app)

def setup_function(): documentos_service._items.clear()

def payload(**overrides):
    data = {'pasta':'Financeiro','titulo':'Ata de reunião','nomeArquivo':'ata.pdf','arquivoCompactadoGzip':'H4sIAAAAA'}
    data.update(overrides)
    return data

def test_document_crud_preserves_file_payload_and_original_name():
    created = client.post('/api/v1/documentos', json=payload())
    assert created.status_code == 201
    item = created.json()
    assert item['nomeArquivo'] == 'ata.pdf'
    assert item['arquivoCompactadoGzip'] == 'H4sIAAAAA'
    assert client.get('/api/v1/documentos/'+item['id']).status_code == 200
    changed = client.put('/api/v1/documentos/'+item['id'], json=payload(titulo='Ata atualizada'))
    assert changed.status_code == 200 and changed.json()['titulo'] == 'Ata atualizada'
    assert client.delete('/api/v1/documentos/'+item['id']).status_code == 204

def test_document_not_found():
    assert client.get('/api/v1/documentos/inexistente').status_code == 404
    assert client.delete('/api/v1/documentos/inexistente').status_code == 404

def test_document_requires_file_content():
    data = payload()
    data['arquivoCompactadoGzip'] = ''
    assert client.post('/api/v1/documentos', json=data).status_code == 422
