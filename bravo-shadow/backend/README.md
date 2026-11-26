# Backend — Bravo Shadow

## Requisitos

- Python 3.11 ou superior.
- Ambiente virtual recomendado.

## Preparação

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

No Windows, ative o ambiente com `.venv\\Scripts\\activate`.

## Verificação

- Saúde: `GET http://127.0.0.1:8000/api/v1/health`
- OpenAPI: `http://127.0.0.1:8000/docs`

## Limites desta etapa

A API não está conectada ao Supabase, não recebe tokens, não lê nem grava dados. CORS, autenticação, autorização, logging estruturado e integração de dados serão definidos após o inventário e a modelagem de segurança.
