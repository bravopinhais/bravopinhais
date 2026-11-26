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


## Revisão de arquitetura

Consulte [`docs/revisao-integracao-arquitetura.md`](../docs/revisao-integracao-arquitetura.md) para a matriz de dependências, riscos prioritários e critérios de prontidão. A API continua em memória e não deve receber dados reais.


## Próxima etapa: persistência PostgreSQL

O modelo do primeiro lote está em [`docs/modelo-persistencia-piloto.md`](../docs/modelo-persistencia-piloto.md). Até a geração e validação de migrations em stack local, os serviços continuam exclusivamente em memória. Não configure `DATABASE_URL` nem credenciais Supabase apontando para produção. A implementação futura usará repositórios injetados, transações para movimentos de estoque e controle otimista por versão.


## Camada de repositórios (primeiro corte)

Foi introduzido `app/core/repositories.py` com o contrato `CollectionRepository` e o adaptador `InMemoryCollectionRepository`. Plano de Contas, Financeiro, Estoque e Acertos de Estoque agora recebem repositórios por injeção no construtor, mantendo o adaptador em memória como padrão da sombra. As rotas HTTP permanecem iguais.

O serviço de Acertos de Estoque deixou de acessar diretamente o dicionário privado do serviço de Estoque: a atualização de saldo passa por `update_quantity`. Isso melhora o isolamento entre módulos, mas **não cria atomicidade** no adaptador em memória. A operação transacional de saldo + histórico continua sendo requisito obrigatório para o adaptador PostgreSQL e bloqueia qualquer uso com dados reais.

Compatibilidade temporária: o atributo `_items` continua exposto internamente pelos serviços para que os testes atuais possam limpar o adaptador em memória. Código novo deve usar os métodos do repositório, não manipular esse atributo.


## Preparação transacional e valores financeiros

O contrato financeiro usa `Decimal` com precisão máxima de 14 dígitos e 2 casas decimais, alinhado ao futuro `numeric(14,2)` do PostgreSQL. O módulo `app/core/transactions.py` define os ports `TransactionalInventoryRepository` e `UnitOfWork` para a futura gravação atômica de movimentos de estoque. Eles ainda não possuem implementação PostgreSQL; os serviços ativos continuam em memória e a movimentação atual ainda não é ACID.
