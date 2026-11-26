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
| Moradores | `GET/POST /api/v1/moradores`, filtros `bloco`/`busca`, `PUT/DELETE /api/v1/moradores/{id}`, `POST /api/v1/moradores/importar` (lote JSON) |
| Pastas | `GET/POST /api/v1/categorias`, `DELETE /api/v1/categorias/{id}` |
| Estoque | `GET/POST /api/v1/estoque`, `PUT/DELETE /api/v1/estoque/{id}` |
| Acertos de estoque | `GET/POST /api/v1/acertos-estoque`, `DELETE /api/v1/acertos-estoque/{id}` |
| Documentos | `GET/POST /api/v1/documentos`, `GET/PUT/DELETE /api/v1/documentos/{id}` |
| Motivos de acerto | `GET/POST /api/v1/motivos-acerto-estoque`, `DELETE /api/v1/motivos-acerto-estoque/{id}` |
| Usuários / Perfis | `GET/POST /api/v1/usuarios`, `GET/PUT/DELETE /api/v1/usuarios/{id}` |

Os quinze módulos usam armazenamento temporário em memória. O verificador de exclusão do Plano de Contas consulta os títulos financeiros mantidos no mesmo processo da API.

## Identidade e segurança

O módulo de usuários gerencia somente perfis e vínculo de e-mail. Não implementa login, senha, validação de token Google ou autorização efetiva. O e-mail será vinculado à identidade autenticada somente após validação server-side do token do provedor adotado pelo ambiente ativo. Não são aceitos campos de senha ou hash.

## Limites desta etapa

A API não está conectada ao Supabase, não recebe tokens, não lê nem grava dados de produção. Os dados são perdidos ao reiniciar o processo. Não há frontend integrado, CORS liberado ou autorização efetiva. CORS por allowlist, integração de identidade, matriz de permissões, logging estruturado e persistência serão definidos após homologação.

## Testes

Há testes automatizados em `backend/tests` para os CRUDs, integridade entre Plano de Contas e Financeiro e perfis de usuário. Foram escritos, mas ainda não executados neste ambiente.
