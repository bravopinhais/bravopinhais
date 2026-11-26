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

## Rotas implementadas na sombra

| Módulo | Rotas |
|---|---|
| Plano de Contas | `GET/POST /api/v1/plano-contas`, `PUT/DELETE /api/v1/plano-contas/{id}` |
| Financeiro | `GET/POST /api/v1/financeiro`, `PUT/DELETE /api/v1/financeiro/{id}` |
| Formas Monetárias | `GET/POST /api/v1/formas-monetarias`, `PUT/DELETE /api/v1/formas-monetarias/{id}` |
| Contas Bancárias | `GET/POST /api/v1/contas-bancarias`, `PUT/DELETE /api/v1/contas-bancarias/{id}` |
| Fornecedores | `GET/POST /api/v1/fornecedores`, `PUT/DELETE /api/v1/fornecedores/{id}` |
| Empregados | `GET/POST /api/v1/empregados`, `PUT/DELETE /api/v1/empregados/{id}` |
| Condomínio | `GET/PUT /api/v1/condominio` (atualização parcial) |
| Conselheiros | `GET/POST /api/v1/conselheiros`, `PUT/DELETE /api/v1/conselheiros/{id}` |

Os oito módulos usam armazenamento temporário em memória. O verificador de exclusão do Plano de Contas consulta os títulos financeiros mantidos no mesmo processo da API.

## Limites desta etapa

A API não está conectada ao Supabase, não recebe tokens, não lê nem grava dados de produção. Os dados são perdidos ao reiniciar o processo. Não há frontend integrado, CORS liberado, autenticação ou autorização. CORS, identidade Google/e-mail, autorização, logging estruturado e persistência serão definidos após o inventário e a modelagem de segurança.

## Testes

Há testes automatizados em `backend/tests` para os CRUDs e para a proteção de integridade entre Plano de Contas e Financeiro. Eles foram escritos, mas ainda não executados neste ambiente.
