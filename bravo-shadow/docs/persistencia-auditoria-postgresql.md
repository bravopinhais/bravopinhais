# Persistência de auditoria PostgreSQL — Bravo Shadow

## Status

**Rascunho de desenho, não migration.** O arquivo `sql-auditoria-rascunho.sql` documenta uma possível tabela privada. Não foi aplicado, não cria roles e não concede acesso à API.

## Estrutura proposta

A tabela `bravo_shadow.audit_events` armazena somente:

- identificador técnico do evento;
- instante UTC com fuso (`timestamptz`);
- `actor_subject` (sujeito Google validado pelo backend, não e-mail);
- ação/capacidade canônica;
- tipo e identificador técnico da entidade;
- resultado (`success`, `denied`, `failure`);
- identificador de correlação da requisição, quando disponível.

Índices propostos cobrem consultas por instante, ator, ação e entidade. Não há coluna JSON de metadata nem payload livre, para reduzir o risco de registrar dados pessoais, tokens ou conteúdo financeiro/documental.

## Privilégios propostos

Separar pelo menos três identidades conceituais, com nomes finais ainda pendentes:

1. **Owner/migration:** controla schema e migrations; nunca usado pela API.
2. **Writer/API:** somente INSERT na tabela de auditoria; sem UPDATE, DELETE, TRUNCATE, DDL ou propriedade.
3. **Reader/auditoria:** SELECT restrito a operadores autorizados; não é a credencial da API comum.

RLS está habilitado e forçado no rascunho, sem policies permissivas. Isso bloqueia acesso por roles comuns até que policies explícitas sejam definidas e testadas. Revogações de roles Supabase são apenas uma camada inicial; a migration final precisa confirmar a existência e os privilégios efetivos dessas roles na stack local.

**Não conceder** `BYPASSRLS`, superuser, ownership, `ALL PRIVILEGES` ou UPDATE/DELETE à identidade de execução. Não criar policy `USING (true)` para contornar bloqueios.

## Integridade e retenção

- A aplicação deve enviar eventos somente após validar a identidade e determinar a ação; `actor_subject` nunca vem do corpo da requisição.
- Operações críticas devem gravar evento e alteração de negócio na mesma transação, quando o desenho transacional permitir. Se a auditoria falhar, a política deve decidir explicitamente entre rollback/negação e fila durável; nunca ignorar silenciosamente.
- Para registrar negações anteriores à transação de negócio, usar transação curta separada e garantir que a falha do log não transforme uma negação em sucesso.
- Não registrar conteúdo de requisição, tokens, e-mails, nomes, CPF, telefone, endereço, arquivo, valores monetários ou segredos.
- Definir retenção, backup, restauração, monitoramento de falhas e acesso de leitura antes de produção. Não há prazo de retenção inventado nesta proposta.
- `INSERT` sem `UPDATE/DELETE` para a role da API fornece append-only no nível de privilégios; owner e administradores de banco continuam sendo uma fronteira de confiança. Não chamar isso de armazenamento inviolável.

## Validação obrigatória no PostgreSQL local

1. Gerar migration com `supabase migration new`; não converter este rascunho em migration manualmente.
2. Aplicar somente em stack local descartável.
3. Inspecionar `pg_roles`, `pg_policies`, `information_schema.role_table_grants` e privilégios efetivos.
4. Provar INSERT permitido para writer e SELECT negado para writer, se essa for a separação aprovada.
5. Provar UPDATE, DELETE, TRUNCATE, DDL e acesso por `anon`, `authenticated` e `service_role` negados.
6. Provar SELECT permitido apenas para reader autorizado.
7. Testar rollback quando uma operação de negócio crítica não consegue registrar auditoria.
8. Testar volume, índices, backup e recuperação sem dados reais.

## Próximos passos

- Revisar o esquema e a política de retenção.
- Definir os nomes e memberships das roles na stack local.
- Implementar o adapter PostgreSQL e injetá-lo somente após testes de integração.
- Integrar eventos primeiro a operações administrativas e críticas, depois aos demais serviços.
- Proteger a consulta de auditoria por capacidade específica, ainda não aprovada.

## Limites preservados

Nenhuma migration foi criada ou aplicada. Nenhuma role, policy, grant ou banco foi alterado. O `AuditSink` em memória continua isolado e não é apresentado como persistência. Nenhum router foi conectado à auditoria e nenhuma rota foi exposta.

## Adaptador Python — etapa isolada

Foi acrescentado `backend/app/core/postgres_audit.py` com `PostgresAuditSink`. Ele recebe uma `connection_factory`, valida que o objeto é um `AuditEvent`, executa somente INSERT parametrizado e usa a unidade de trabalho existente para commit/rollback/close. Não oferece métodos de consulta, alteração ou exclusão.

Os testes em `backend/tests/test_postgres_audit.py` cobrem parâmetros enviados, commit, rollback em falha e rejeição de objeto inválido antes de abrir conexão. **Foram escritos, mas não executados.** Usam conexão simulada e não comprovam compatibilidade com PostgreSQL real, RLS ou GRANTs.

O adaptador permanece deliberadamente fora de `storage.py` e `main.py`: não há tabela aplicada, credencial writer configurada, nem prova de que a role de conexão possua somente INSERT. A atomicidade conjunta agora é tecnicamente possível por `append_in_transaction`, mas ainda não foi adotada por nenhum serviço nem comprovada em PostgreSQL real. Portanto, o adaptador ainda não deve ser usado como trilha de auditoria operacional.


## Inserção na transação do serviço — atualização

O adaptador também expõe `append_in_transaction(connection, event)`. Esse método executa o INSERT na conexão fornecida pelo serviço, fecha somente o cursor e **não** executa commit, rollback ou close. Assim, um serviço que já controla uma unidade de trabalho pode incluir o evento antes do commit e confirmar ou reverter a alteração de negócio e a auditoria em conjunto.

O método `append(event)` continua disponível para uma transação independente, útil em contextos isolados, mas não garante atomicidade com uma operação de negócio que use outra conexão. Não usar esse caminho como substituto da gravação integrada em operações críticas.

Foram acrescentados testes unitários simulados para verificar que `append_in_transaction` não assume a propriedade da conexão, inclusive quando o INSERT falha. Os testes ainda não foram executados e não substituem testes de integração com PostgreSQL local. Nenhum serviço ou router foi conectado ao adaptador.
