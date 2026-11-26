# Matriz proposta de roles e permissões — Bravo Shadow

**Status:** proposta técnica para revisão. Não cria roles, policies, grants ou migrations.
**Objetivo:** definir a separação entre autenticação de pessoas, autorização no backend e privilégios do PostgreSQL para o ledger de revisão de migração.

## 1. Decisão arquitetural proposta

Adotar autorização de usuário na camada de serviço (estratégia B do parecer), com RLS como defesa adicional baseada na role técnica da conexão.

Motivo: o adaptador atual usa uma conexão PostgreSQL por unidade de trabalho e não possui mecanismo seguro e aprovado para propagar identidade de usuário até o banco. Não se deve inventar um contexto de sessão ou aceitar um identificador de ator do cliente. O backend já valida o token Google e resolve um `AuthenticatedPrincipal`; essa identidade será a fonte da autorização por pessoa.

**Limite importante:** essa estratégia não faz RLS distinguir cada usuário final. A RLS limita o acesso técnico à role privada do backend; a autorização individual por usuário acontece no backend, em toda chamada. Se futuramente for exigido isolamento por usuário diretamente no banco, será necessário projetar e testar um contexto transacional confiável antes de criar policies.

## 2. Matriz de papéis PostgreSQL proposta

| Papel lógico | Login | Propriedade/atributos | Acesso pretendido |
|---|---:|---|---|
| `bravo_shadow_owner` | Não | Owner do schema/tabelas; sem uso pela API | DDL e ownership em migrations controladas |
| `bravo_shadow_migrator` | Controlado | Papel operacional temporário; recebe privilégios de owner somente durante migration aprovada | Aplicar migrations locais revisadas; nunca usado pelo backend |
| `bravo_shadow_runtime` | Não | Papel de grupo, sem ownership, sem superuser e sem BYPASSRLS | Privilégios mínimos do backend para o ledger |
| login técnico do backend | Sim | Membro de `bravo_shadow_runtime`; sem grants diretos adicionais | Conectar como backend e assumir somente os privilégios do grupo |

Os nomes são lógicos e ainda não são DDL. Em Supabase, a implementação deve ser compatível com o modelo de roles gerenciadas; não alterar roles internas nem conceder acesso a `service_role` como substituto.

A role de migration não deve ser usada em processos web, workers ou tarefas de rotina. O login técnico do backend não deve ser owner nem membro de papéis administrativos.

## 3. Matriz de operações no ledger

| Operação | Backend autenticado | Runtime no banco | Observação |
|---|---|---|---|
| Consultar lote/fila/histórico | Capacidade `migration_review:read` | SELECT somente nas três tabelas | Verificar lote e hash em cada consulta |
| Registrar revisão | Capacidade `migration_review:append` | SELECT necessário + INSERT somente em events | `reviewer_id` vem de `principal.subject` |
| Inicializar snapshot | Serviço interno controlado; não endpoint público | INSERT em batches/decisions apenas durante preparação | Não expor ao usuário final |
| UPDATE de evento | Negado | Sem UPDATE | Correção por novo evento |
| DELETE de evento | Negado | Sem DELETE | Histórico append-only |
| DDL/alterar RLS/grants | Negado | Sem CREATE/ALTER/OWNER | Somente migration controlada |
| Executar importação/cutover | Fora deste ledger | Nenhum privilégio concedido por este desenho | Exige fluxo e aprovação separados |

As capacidades acima são nomes propostos, ainda não adicionados ao catálogo `CAPABILITIES` e não concedidos a nenhum perfil. Não presumir que Admin ou Operador já esteja autorizado.

## 4. Policies RLS — limites para a futura migration

A migration final deverá:
- habilitar e forçar RLS nas três tabelas;
- conceder acesso de schema/tabela somente à role técnica privada necessária;
- criar policies explícitas para `bravo_shadow_runtime` limitadas às operações previstas;
- não criar policy para `PUBLIC`, `anon`, `authenticated` ou `service_role`;
- não conceder UPDATE/DELETE em `migration_review_events`;
- manter ownership separado do runtime;
- testar o comportamento como owner, migrator, runtime e roles Supabase padrão.

Como a autorização individual fica no backend, uma policy para a role runtime não substitui as verificações `migration_review:read` e `migration_review:append`. Nenhum endpoint deve ser habilitado antes de ambas as camadas estarem testadas.

## 5. Regras para o backend

1. Validar token Google no servidor por `get_current_principal`.
2. Rejeitar usuário inativo, identidade ausente ou perfil desconhecido.
3. Aplicar capacidade específica em cada endpoint, sem confiar na interface.
4. Derivar `reviewer_id` de `principal.subject`; ignorar ou rejeitar esse campo no request.
5. Não aceitar do cliente `batch_key` sem reconstruir/verificar o manifesto e conferir autorização de acesso ao lote.
6. Manter `initialize` fora das rotas públicas.
7. Não expor adaptador SQL diretamente como endpoint.
8. Não permitir que revisão aprovada acione importação automaticamente.

## 6. Pré-requisitos antes de escrever DDL de roles/policies

- Aprovar a matriz de capacidades por perfil Bravo.
- Confirmar o modelo de conexão local e Supabase sem credenciais privilegiadas no backend.
- Definir como a role de migration será assumida de forma controlada no ambiente local.
- Definir o login técnico privado e sua associação à role de grupo.
- Escrever migration idempotente e revisada com grants mínimos.
- Executar testes locais com roles reais, incluindo tentativas de elevação e acesso cruzado.
- Revisar logs para não registrar tokens Google, connection strings ou segredos.

## 7. Casos de teste obrigatórios

- Login técnico não é owner, superuser nem `BYPASSRLS`.
- Login técnico não consegue criar schema, tabela, policy, role ou grant.
- Runtime não consegue UPDATE/DELETE eventos.
- Runtime sem grants/policy não acessa tabelas.
- Usuário Bravo sem capacidade recebe 403 mesmo com token Google válido.
- Usuário autorizado não consegue forjar `reviewer_id`.
- Falha de autenticação/autorizações ocorre antes de qualquer escrita.
- Lote/hash divergente falha sem revelar dados de outro lote.
- Acesso via `anon`, `authenticated` e `service_role` não é liberado por engano.
- Migração local e rollback são testados em banco descartável.

## 8. Estado atual e bloqueios

Nenhuma role foi criada. Nenhuma policy ou grant foi aplicada. O catálogo de capacidades permanece inalterado. O adaptador PostgreSQL continua desconectado. O SQL permanece rascunho e não foi executado.

A proposta deliberadamente não habilita acesso: ela organiza o próximo desenho para revisão e aprovação antes de qualquer DDL.
