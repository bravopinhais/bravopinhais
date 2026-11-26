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

Os quinze módulos usam armazenamento temporário em memória por padrão. Plano de Contas, Financeiro e Formas Monetárias recebem serviços/repositórios próprios por instância FastAPI; o verificador de exclusão do Plano de Contas consulta os títulos financeiros da mesma instância. As demais rotas ainda usam serviços em memória no escopo atual.

## Identidade e segurança

O módulo de usuários gerencia somente perfis e vínculo de e-mail. Não implementa login, senha, validação de token Google ou autorização efetiva. O e-mail será vinculado à identidade autenticada somente após validação server-side do token do provedor adotado pelo ambiente ativo. Não são aceitos campos de senha ou hash.

## Limites desta etapa

A API não está conectada ao Supabase, não recebe tokens, não lê nem grava dados de produção. Os dados são perdidos ao reiniciar o processo. Não há frontend integrado, CORS liberado ou autorização efetiva. CORS por allowlist, integração de identidade, matriz de permissões, logging estruturado e persistência serão definidos após homologação.

## Testes

Há testes automatizados em `backend/tests` para os CRUDs, integridade entre Plano de Contas e Financeiro, perfis de usuário, adaptadores PostgreSQL com conexões falsas, seleção explícita do armazenamento e fluxos HTTP completos sobre repositórios PostgreSQL simulados. Eles foram escritos, mas ainda não executados neste ambiente. Os testes com conexão falsa validam SQL/fluxos de commit e rollback; não substituem os testes de integração contra PostgreSQL local.


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


### Unidade de trabalho PostgreSQL (infraestrutura inicial)

Foi adicionado `app/core/postgres.py`, com `PostgresUnitOfWork`. Ele recebe uma fábrica de conexões injetada, abre uma conexão por unidade de trabalho, confirma com `commit` quando não há exceção, executa `rollback` em caso de falha e sempre fecha a conexão. A fábrica Psycopg 3 lê `BRAVO_DATABASE_URL` no backend e só abre conexão quando uma operação SQL é chamada. Não há pool; cada operação abre e fecha uma conexão.

Os testes com conexão falsa cobrem o ciclo de commit/rollback/close, e os testes financeiros agora incluem limites de precisão decimal. Os testes foram adicionados ao repositório, mas ainda precisam ser executados em ambiente Python.


### Repositórios PostgreSQL — primeiro adaptador SQL

Foi adicionado `app/core/postgres_repositories.py` com adaptadores DB-API para Plano de Contas e Financeiro. As consultas usam parâmetros, schema explícito `bravo_shadow`, mantêm `Decimal` no valor financeiro e convertem `planoContaId=""` para SQL `NULL` (e vice-versa na leitura). Cada método abre sua própria unidade de trabalho; falhas provocam rollback. A exclusão de conta traduz violação de FK (`23503`) em conflito HTTP 409.

Os adaptadores são selecionados pela configuração explícita `create_app(storage_backend="postgres", postgres_connection_factory=...)`; as rotas de Plano de Contas e Financeiro passam a operar por esses repositórios quando esse modo é selecionado. O driver Psycopg 3.3.9 está fixado em `requirements.txt`; nenhuma URL foi definida, nenhuma tabela foi criada e a conexão não foi testada. A camada SQL pressupõe que a migration local do modelo já tenha sido aplicada. Não aponte uma fábrica de conexão para produção.

Foram adicionados testes com conexão/cursor falsos para conferir SQL parametrizado, mapeamento de valores, conversão NULL/ string vazia, commit e rollback. Eles ainda não foram executados. Os adaptadores PostgreSQL agora oferecem `replace_if_version`: o UPDATE inclui `WHERE id = %s AND version = %s`, incrementa a versão e, se não atualizar linha, distingue registro inexistente (404) de versão desatualizada (409) na mesma transação. As consultas de leitura também retornam `version`, e os schemas de resposta expõem esse campo. **A API exige `If-Match` nas rotas PUT**, com comparação atômica no adaptador em memória. Os adaptadores PostgreSQL oferecem a operação SQL equivalente, mas ainda não estão injetados nas rotas.


### Resiliência da unidade de trabalho

A unidade de trabalho também trata falha durante o próprio `commit`: tenta executar `rollback`, libera a conexão em seguida e propaga a exceção original. O teste correspondente foi adicionado com conexão falsa. Isso cobre o fluxo de controle, mas ainda não substitui teste de integração com PostgreSQL real.


### Concorrência otimista — camada de repositório

Os adaptadores PostgreSQL implementam `replace_if_version` para Plano de Contas e Financeiro. O cliente obtém `version` na leitura e a camada de aplicação encaminha a versão esperada; atualização obsoleta retorna HTTP 409 e ID inexistente retorna 404. **Nas rotas HTTP atuais, o contrato `If-Match` já está ativo com o adaptador em memória:** ausência do cabeçalho retorna 428, formato inválido retorna 400 e versão obsoleta retorna 409. A comparação e substituição em memória são atômicas sob lock. Os adaptadores PostgreSQL têm a operação SQL equivalente e são injetados nas rotas quando o modo PostgreSQL é selecionado explicitamente. A integração PostgreSQL deve ocorrer somente após migration local, driver escolhido e testes de integração em banco isolado.


### Controle de versão HTTP (Plano de Contas e Financeiro)

As rotas POST devolvem a versão no corpo e um ETag forte no cabeçalho de resposta. As rotas PUT exigem o cabeçalho `If-Match: "n"`; sem esse cabeçalho retornam 428, formato inválido retorna 400 e versão desatualizada retorna 409. A comparação e substituição do adaptador em memória são atômicas sob lock, e os adaptadores PostgreSQL oferecem a operação SQL equivalente. Isso protege as rotas de homologação contra atualização obsoleta. A configuração Psycopg já está disponível, mas o uso real permanece bloqueado até migration local, privilégios mínimos e testes de integração. O cliente deve obter a versão mais recente antes de editar e reenviar a ETag recebida.


## Seleção explícita do armazenamento

A aplicação é criada por `create_app()`. O padrão é `BRAVO_STORAGE_BACKEND=memory`; nesse modo, Plano de Contas e Financeiro usam repositórios temporários em memória, como os demais módulos.

A infraestrutura aceita `create_app(storage_backend="postgres", postgres_connection_factory=...)`. Se a fábrica não for injetada, a aplicação monta uma fábrica Psycopg 3 a partir de `BRAVO_DATABASE_URL`; a variável é obrigatória nesse modo. O driver é importado somente quando PostgreSQL é selecionado. A fábrica não abre conexão no startup: cada operação do repositório abre e fecha sua própria conexão/transação. Sem URL ou driver, a inicialização falha explicitamente e não há fallback para memória.

**Escopo atual:** Plano de Contas, Financeiro e Formas Monetárias têm adaptadores PostgreSQL. Os outros módulos continuam em memória. O driver Psycopg 3.3.9 está declarado e fixado em `requirements.txt`, mas ainda não há migration aplicada, concessão de privilégios ao usuário dedicado da API nem teste contra banco real. Portanto, não habilite PostgreSQL até preparar o schema privado `bravo_shadow`, criar um usuário local de privilégio mínimo e validar os adaptadores. O health endpoint informa o modo configurado, mas não verifica a conectividade com o banco.


### Integração das rotas com adaptadores PostgreSQL (simulada)

O teste `test_postgres_api_integration.py` cria a aplicação com `storage_backend="postgres"` e uma fábrica DB-API falsa, mantendo estado isolado por teste. Ele percorre criação e leitura de conta e título, atualização com ETag, rejeição de versão obsoleta, bloqueio de exclusão por vínculo financeiro e rejeição de código duplicado. Isso valida a ligação entre rotas, serviços, seleção de storage e adaptadores SQL sem acessar banco externo. A simulação não substitui execução contra PostgreSQL real; os testes ainda precisam ser executados no ambiente Python.


A camada Financeiro também traduz violações de chave estrangeira ao criar ou atualizar títulos com uma conta inexistente para HTTP 409. Os testes cobrem os caminhos de repositório e a resposta da rota, preservando rollback e evitando erro interno não tratado.



### Isolamento de serviços por instância

A fábrica `build_storage_services()` cria os três serviços do piloto para cada chamada de `create_app()`. Os routers obtêm a instância correspondente por `request.app.state.services`; não há reconfiguração de singletons globais ao iniciar outra aplicação. Isso permite testes e ambientes paralelos com backends diferentes sem compartilhar os repositórios do piloto. O isolamento está coberto por testes HTTP que criam duas aplicações independentes. Esses testes foram adicionados, mas precisam ser executados no CI/ambiente Python antes de considerar o gate validado.
