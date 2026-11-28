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

Antes de ligar o adaptador à API, separar claramente:
- adaptador/serviço de preparação, executado com credencial de migration controlada;
- adaptador de leitura e append de eventos, executado com credencial runtime.

Não reutilizar uma única connection factory privilegiada para ambos os contextos. Adicionar testes que confirmem que a camada runtime não expõe `initialize` e que falhas de privilégio são propagadas sem fallback para memória.

## 7. Portões de liberação

Não produzir DDL final até:
- aprovar matriz de capacidades por perfil;
- confirmar modelo real de roles no PostgreSQL/Supabase local;
- confirmar como a role de migration será isolada;
- ajustar o adaptador para separar preparação de runtime;
- criar testes de integração com roles reais;
- revisar SQL, policies e grants em conjunto.

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

Foi identificado que o adaptador runtime ainda usa `SELECT ... FOR UPDATE` nas tabelas de batches e decisions. Esse bloqueio exige privilégio UPDATE além de SELECT no PostgreSQL, portanto conflita com a matriz mínima definida nesta especificação.

**Diretriz de desenho para a próxima revisão (ainda não implementada):**
- Remover bloqueios de linha `FOR UPDATE` do caminho runtime.
- Avaliar um bloqueio consultivo transacional PostgreSQL, adquirido antes da leitura da versão corrente e mantido até commit/rollback.
- Para a primeira implementação, preferir uma chave global fixa do subsistema de revisão: reduz a concorrência entre decisões, mas evita colisões de hash e simplifica a prova de exclusão mútua. A otimização para bloqueios por decisão fica para depois de homologação.
- Manter `UNIQUE (batch_key, decision_id, version)` como última barreira de integridade, além de `PRIMARY KEY (event_id)`.
- Manter o teste de duas conexões concorrentes na mesma decisão/versão: exatamente uma grava e a outra recebe `stale_review_version`.
- Acrescentar teste de integração executando append com uma role runtime real, sem UPDATE nas tabelas de batches/decisions, verificando também a permissão necessária para chamar a função de advisory lock.
- Confirmar que o bloqueio é transacional e liberado tanto no commit quanto no rollback.
- Se a constraint de versão detectar disputa inesperada, tratar a violação específica de unicidade como conflito de versão, sem mascarar violações de outras constraints.

A chave global é uma escolha conservadora de homologação, não uma decisão de desempenho definitiva. O grant EXECUTE da função de advisory lock deve ser verificado explicitamente no ambiente descartável; não presumir que os privilégios padrão permanecerão iguais após hardening.

**Estado:** análise e diretriz documental בלבד. O adaptador, o SQL rascunho, as roles e as policies não foram alterados nem executados.