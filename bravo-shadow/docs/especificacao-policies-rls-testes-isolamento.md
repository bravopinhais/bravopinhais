# Especificação de policies RLS e testes de isolamento — Bravo Shadow

**Status:** desenho técnico não executável. Não cria policies, roles, grants ou migrations.
**Base:** matriz proposta de roles, contrato SQL e revisão de segurança do ledger de migração.

## 1. Modelo de segurança escolhido para o desenho

A autorização por pessoa fica no backend. A RLS funciona como segunda barreira para restringir o acesso SQL à role técnica privada do Bravo Shadow.

- Google ID token validado pelo backend.
- Usuário vinculado a cadastro interno ativo.
- Capacidade de leitura ou inclusão validada em cada endpoint.
- `reviewer_id` sempre derivado de `AuthenticatedPrincipal.subject`.
- O banco não recebe identidade de usuário final escolhida pelo navegador.
- RLS não será descrita como isolamento por usuário final: nesta arquitetura, ela restringe a role técnica do backend.

Se futuramente houver exigência de RLS por usuário, será um projeto separado com contexto transacional autenticado, propagação segura em pool/conexões e testes de spoofing.

## 2. Escopo de cada tabela

| Tabela | Leitura runtime | Escrita runtime | Imutabilidade |
|---|---|---|---|
| `migration_review_batches` | SELECT | nenhuma | sem UPDATE/DELETE |
| `migration_review_decisions` | SELECT | nenhuma | fotografia não mutável |
| `migration_review_events` | SELECT | INSERT | sem UPDATE/DELETE |

A inicialização do lote e da fotografia de decisões não será uma operação normal da API. A preparação do snapshot será executada por fluxo interno de migração controlado, com credencial separada e aprovada. O runtime não recebe INSERT nessas duas tabelas nesta primeira versão.

O runtime recebe INSERT apenas em `migration_review_events`, além dos SELECT necessários. As constraints, FKs e unicidades do schema continuam obrigatórias; RLS não substitui integridade referencial.

## 3. Diretrizes para policies futuras

A migration final deve, em conjunto e na mesma revisão:

1. Confirmar ownership separado da role runtime.
2. Garantir runtime sem atributos `SUPERUSER`, `BYPASSRLS`, `CREATEDB`, `CREATEROLE` ou ownership das tabelas.
3. Habilitar e forçar RLS nas três tabelas.
4. Criar policies explícitas direcionadas somente à role privada runtime para SELECT nas três tabelas e INSERT em events.
5. Não criar policy para `PUBLIC`, `anon`, `authenticated` ou `service_role`.
6. Não conceder UPDATE/DELETE em nenhuma tabela do ledger ao runtime.
7. Não conceder DDL, TRUNCATE, REFERENCES, TRIGGER ou privilégios de administração ao runtime.
8. Manter acesso de migration fora da role runtime e fora do processo web.

A role de migration pode ser owner e ter autoridade administrativa apenas durante execução controlada. Se `FORCE ROW LEVEL SECURITY` estiver ativo, o comportamento do owner/migrator precisa ser explicitamente testado; não presumir bypass implícito. Não adicionar policy administrativa ampla sem documentar como a credencial é isolada e usada.

## 4. Grants mínimos a avaliar

Os grants finais devem ser específicos por tabela e operação, não concedidos ao schema inteiro sem necessidade:

- USAGE no schema para a role runtime.
- SELECT em batches, decisions e events.
- INSERT em events.
- Nenhum INSERT em batches/decisions para runtime nesta primeira versão.
- Nenhum UPDATE, DELETE, TRUNCATE, REFERENCES ou TRIGGER.
- Nenhum CREATE no schema.
- Nenhuma associação do runtime a owner/migrator ou roles privilegiadas.

A migration deve revogar privilégios herdados de PUBLIC e revisar privilégios padrão do schema. Em Supabase, validar as roles gerenciadas e a forma suportada de conceder membership; não modificar roles internas.

## 5. Testes locais de RLS e grants

Executar em PostgreSQL local descartável, nunca com dados reais. Usar conexões separadas autenticadas como cada role; não simular troca de role com a mesma conexão privilegiada como único teste.

| Identidade de teste | SELECT | INSERT events | INSERT batch/decision | UPDATE/DELETE | DDL |
|---|---:|---:|---:|---:|---:|
| runtime | permitido | permitido | negado | negado | negado |
| migrator controlado | conforme procedimento de migration | fora do runtime | permitido só na preparação | sem alteração de histórico após carga | permitido somente no ciclo controlado |
| anon | negado | negado | negado | negado | negado |
| authenticated | negado | negado | negado | negado | negado |
| service_role | negado por grants deste schema privado | negado | negado | negado | negado |
| owner | testar efeito de FORCE e ownership | testar | testar | testar | conforme ownership |

Além da matriz:
- Sem policy e sem grant, o runtime não acessa nenhuma tabela.
- Runtime não consegue alterar policies, grants, owners ou atributos de roles.
- Runtime não consegue consultar schema/tabelas fora do escopo concedido por acidente.
- Hash de lote divergente em decisão/evento falha pela FK composta.
- Evento de decisão inexistente ou lote incorreto falha pela FK composta.
- Mesmo `decision_id` com manifesto diferente falha.
- UPDATE/DELETE falham tanto por SQL direto quanto pela API.
- SELECT de lote não autorizado é negado pelo backend antes de executar SQL.
- Token Google válido sem capacidade recebe 403 antes de qualquer escrita.
- Campo `reviewer_id` enviado no body não altera o ator derivado do principal.
- Concorrência de duas conexões para mesma versão: uma grava; outra recebe conflito.
- Erro após INSERT e antes do commit causa rollback.
- Snapshot alterado ou ausente falha fechado.

## 6. Testes de regressão do adaptador

O adaptador atual foi escrito para um contrato de schema no qual `initialize` insere batches e decisions. Com a matriz de privilégios acima, runtime não poderá chamar `initialize`.

A separação foi implementada:
- `PostgresReviewSnapshotInitializer` executa a preparação com connection factory própria;
- `PostgresReviewRuntimeStore` expõe somente leitura e append, com connection factory independente;
- a camada runtime não expõe `initialize` e não possui fallback para memória.

Os testes de integração agora autenticam uma sessão PostgreSQL independente como role runtime de teste (LOGIN próprio), em vez de depender apenas de `SET ROLE` numa sessão administrativa. A validação continua restrita ao PostgreSQL descartável.

## 7. Portões de liberação

Não produzir DDL final até:
- aprovar matriz de capacidades por perfil;
- confirmar modelo real de roles no PostgreSQL/Supabase local;
- confirmar como a role de migration será isolada;
- ajustar o adaptador para separar preparação de runtime;
- revisar SQL, policies e grants em conjunto no ambiente local/Supabase antes de qualquer conexão externa;
- confirmar separadamente a configuração de roles do projeto hospedado, sem executar alterações remotas nesta fase.

Não executar `supabase link`, `db push`, `--remote` ou qualquer comando contra projeto hospedado. Nenhum dado legado deve ser lido ou importado nesta fase.

## 8. Estado atual

Esta especificação continua sendo apenas documentação. Nenhuma policy foi criada e nenhum grant foi concedido à aplicação. O banco permanece desconectado e não houve importação de dados.

**Homologação PostgreSQL descartável do vínculo Google:** concluída com sucesso na execução CI `46147967637`, commit `94fefd65ef49464e3b72e407acb393b09c2fea09`. Os testes cobrem:
- FK para conta Bravo existente;
- rejeição de issuer, subject, e-mail verificado e ator administrativo inválidos;
- unicidade de uma identidade por conta e de uma conta por identidade Google;
- concorrência de duas conexões tentando registrar o mesmo issuer/subject;
- RLS habilitada e forçada;
- ausência de privilégios SELECT/INSERT/UPDATE/DELETE para `anon`, `authenticated` e `service_role`.

**Limite da evidência:** os testes de privilégio consultam `has_table_privilege` e metadados do catálogo; ainda não executam sessões autenticadas separadamente como cada role nem validam o comportamento de policies runtime. A matriz completa descrita nesta especificação continua pendente. O vínculo Google ainda não é consumido pelo fluxo de autenticação, que permanece baseado no e-mail verificado e no cadastro interno ativo.


## 9. Concorrência do append sem privilégio UPDATE

O uso de `SELECT ... FOR UPDATE` no caminho runtime foi removido porque exigiria privilégio UPDATE nas tabelas imutáveis de batches/decisions.

**Implementação Shadow atual:**
- `append` adquire `pg_catalog.pg_advisory_xact_lock` com uma chave global fixa do subsistema antes de consultar lote, decisão e versão.
- O bloqueio é transacional e é liberado automaticamente no commit ou rollback.
- A chave global serializa todos os appends deste subsistema. É uma escolha conservadora de homologação: reduz paralelismo, mas evita colisões de hash e simplifica a prova de exclusão mútua.
- Os SELECTs de batches/decisions não usam `FOR UPDATE`.
- A role runtime precisa de SELECT nas três tabelas, INSERT somente em events e EXECUTE na função de advisory lock. Não precisa de UPDATE nas tabelas de snapshot.
- Permanecem as barreiras `UNIQUE (batch_key, decision_id, version)` e `PRIMARY KEY (event_id)`.

**Testes CI:** execução `46152084098`, commit `809ed5e7e329e068c21d34ac430440cec2b6d97d`, concluída com sucesso. Passaram testes unitários, smoke test Docker e integrações PostgreSQL descartável. A integração autentica conexões independentes como a role runtime e como `anon`, `authenticated` e `service_role` sintéticas. Confirma que as três roles de cliente não conseguem ler nem inserir no ledger; runtime consegue executar load/append com SELECT/INSERT mínimos, mas não consegue UPDATE/DELETE, inserir snapshots ou executar DDL. RLS é forçada nas três tabelas e o runtime não recebe UPDATE nos snapshots. Também permanecem aprovados os testes concorrentes de mesma versão, gravações em decisões distintas, rollback e unicidade global de event_id.

**Limite da evidência:** a homologação usa PostgreSQL local descartável, credenciais e policies sintéticas. Não comprova os grants, policies ou comportamento de um projeto Supabase hospedado. A credencial de preparação/migration ainda precisa de um procedimento operacional separado e de teste próprio de isolamento. O SQL de schema continua rascunho; nenhum banco externo foi conectado, alterado ou importado.
