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

Nenhuma migration foi criada ou aplicada. Nenhuma role, policy, grant ou banco foi alterado. O `AuditSink` em memória continua isolado e não é apresentado como persistência. A rota de desativação lógica constrói um evento de sucesso e o repositório PostgreSQL sabe inseri-lo atomicamente, mas a capacidade permanece sem concessão e o sink ainda não foi validado em banco real. Não existe consulta de auditoria exposta.

## Adaptador Python — etapa isolada

Foi acrescentado `backend/app/core/postgres_audit.py` com `PostgresAuditSink`. Ele recebe uma `connection_factory`, valida que o objeto é um `AuditEvent`, executa somente INSERT parametrizado e usa a unidade de trabalho existente para commit/rollback/close. Não oferece métodos de consulta, alteração ou exclusão.

Os testes em `backend/tests/test_postgres_audit.py` cobrem parâmetros enviados, commit, rollback em falha e rejeição de objeto inválido antes de abrir conexão. **Foram escritos, mas não executados.** Usam conexão simulada e não comprovam compatibilidade com PostgreSQL real, RLS ou GRANTs.

O adaptador permanece deliberadamente fora de `storage.py` e `main.py`: não há tabela aplicada, credencial writer configurada, nem prova de que a role de conexão possua somente INSERT. A atomicidade conjunta agora é tecnicamente possível por `append_in_transaction`, mas ainda não foi adotada por nenhum serviço nem comprovada em PostgreSQL real. Portanto, o adaptador ainda não deve ser usado como trilha de auditoria operacional.


## Inserção na transação do serviço — atualização

O adaptador também expõe `append_in_transaction(connection, event)`. Esse método executa o INSERT na conexão fornecida pelo serviço, fecha somente o cursor e **não** executa commit, rollback ou close. Assim, um serviço que já controla uma unidade de trabalho pode incluir o evento antes do commit e confirmar ou reverter a alteração de negócio e a auditoria em conjunto.

O método `append(event)` continua disponível para uma transação independente, útil em contextos isolados, mas não garante atomicidade com uma operação de negócio que use outra conexão. Não usar esse caminho como substituto da gravação integrada em operações críticas.

Foram acrescentados testes unitários simulados para verificar que `append_in_transaction` não assume a propriedade da conexão, inclusive quando o INSERT falha. Os testes ainda não foram executados e não substituem testes de integração com PostgreSQL local. Nenhum serviço ou router foi conectado ao adaptador.

## Revisão de rastreabilidade e minimização — 26/11/2026

A revisão confirmou que `AuditEvent` contém somente oito campos explícitos: `actor_subject`, `action`, `entity_type`, `entity_id`, `outcome`, `request_id`, `event_id` e `occurred_at`. Foram adicionados testes de contrato para impedir a inclusão acidental de campos livres como e-mail ou metadata/token.

**Limitação inicial de correlação (superada parcialmente):** o middleware gera o `request_id` no servidor e a rota de desativação lógica o propaga ao evento. A cobertura ainda é somente desse fluxo; os demais endpoints e eventos de negação/falha não estão integrados.

**Classificação do identificador:** `actor_subject` evita gravar e-mail, mas o `sub` Google continua sendo um identificador pseudônimo vinculável a uma pessoa. Deve receber proteção, controle de leitura e prazo de retenção definidos; não é dado anônimo.

Os testes adicionados ainda não foram executados nesta etapa. O sink PostgreSQL permanece desconectado da aplicação, e o SQL continua rascunho não aplicado.

## Contexto HTTP de requisição — etapa inicial

A API agora gera um identificador `req_<uuid>` no middleware, guarda-o em `request.state.request_id` e o devolve no cabeçalho `X-Request-ID`. O valor é sempre criado no servidor; um `X-Request-ID` recebido do cliente é ignorado, evitando que o chamador escolha o identificador usado para correlação interna.

Foram adicionados testes para formato, unicidade entre requisições e rejeição de tentativa de falsificação pelo cabeçalho de entrada. **Esses testes foram escritos, mas não executados nesta etapa.**

**Limite explícito desta etapa:** o request ID é propagado somente na desativação lógica. Não há rastreabilidade ponta a ponta para todos os endpoints; nunca aceitar `actor_subject`, perfil ou e-mail do corpo/cabeçalhos.

### Propagação para desativação lógica — código preparado

O endpoint de desativação lógica agora encaminha `request.state.request_id` ao serviço; o serviço o inclui em `AuditEvent.request_id`. O identificador vem exclusivamente do middleware server-side. Foi atualizado o teste unitário do serviço para conferir a presença do valor no evento.

Essa ligação cobre somente o fluxo de desativação lógica. A alteração administrativa de perfil/status ainda não tem rota e não foi conectada. A capacidade `usuarios:deactivate` continua sem concessão na matriz; portanto, o endpoint permanece bloqueado para Admin e Operador. A integração não ativa permissões nem conecta o sink PostgreSQL.


## Identidade do ator na desativação lógica

A rota entrega ao serviço o objeto `AuthenticatedPrincipal` retornado pela dependência de autenticação Google. O serviço não recebe mais `actor_subject` e `actor_email` como campos independentes: valida o tipo, o subject, o e-mail e o status ativo do principal, e grava no evento de auditoria o subject desse mesmo objeto. A comparação de auto-desativação continua usando o e-mail verificado, pois o vínculo persistente por Google `sub` ainda não foi implementado. Essa alteração reforça o contrato interno, mas não cria vínculo durável de identidade nem habilita a capacidade `usuarios:deactivate`.


## Matriz de cobertura: sucesso, negação e falha — revisão 26/11/2026

A revisão do código confirmou que a trilha ainda **não registra de forma geral** tentativas negadas ou falhas. O campo `outcome` aceita `success`, `denied` e `failure`, mas isso é apenas capacidade do modelo de evento, não prova de emissão nem persistência.

| Situação | Estado atual |
|---|---|
| Desativação lógica concluída | O serviço constrói evento `success`; o repositório PostgreSQL insere-o na mesma transação da mudança. O sink só existe no modo PostgreSQL, ainda não validado em banco real. |
| Desativação bloqueada por último Admin, usuário inexistente ou estado inválido | A transação é revertida e nenhum evento `denied` é emitido. |
| Falha ao inserir auditoria durante desativação | A mudança é revertida; a exceção é propagada. Não há evento secundário de `failure`. |
| Falha de autenticação Google / token inválido | A requisição recebe erro, mas não existe evento de auditoria ligado a esse fluxo. |
| Identidade válida sem capacidade autorizada | A dependência responde 403, mas não emite evento `denied`. |
| Erro inesperado em outro endpoint | Não há captura geral que gere evento `failure`. |

### Regras para a próxima integração

- Para negação após autenticação, registrar `denied` em transação curta independente, usando o `sub` do principal validado, ação/capacidade canônica e `request_id`. Nunca incluir corpo, query string, e-mail ou mensagem bruta de exceção.
- Para falha de negócio após autenticação, registrar `failure` em transação separada somente depois do rollback da transação de negócio; se o registro falhar, manter a falha original e emitir métrica/log operacional sem dados pessoais.
- Para falha de autenticação sem identidade validada, **não inventar um ator** nem gravar token, e-mail informado ou IP na tabela atual. Se for necessário auditar esse cenário, desenhar evento de segurança separado com ator anônimo explícito e política de retenção/abuso própria.
- Não registrar falhas de validação com conteúdo do usuário; usar códigos estáveis e categorizados.
- Evitar duplicar evento `success` quando uma operação idempotente já estava concluída.

Nenhuma dessas rotas de emissão adicional foi implementada nesta revisão. O modelo aceita os três resultados e agora possui teste de contrato para isso; os testes foram escritos, não executados. A integração operacional permanece limitada ao sucesso da desativação lógica, e mesmo esse fluxo depende da tabela/role PostgreSQL ainda não aplicadas ou validadas.


## Negações de autorização autenticadas — preparação no código

A dependência central `require_capability_dependency` agora tenta registrar `AuditEvent` com resultado `denied` quando a identidade já foi validada e a capacidade é negada. O evento contém somente o `sub` Google, a capacidade solicitada, o tipo técnico `authorization`, o resultado e o `request_id` gerado pelo middleware. Não inclui e-mail, corpo, query string, IP ou mensagem da exceção.

A gravação usa `audit_sink.append`, em transação independente da operação de negócio. Se o sink falhar, a exceção é registrada no log operacional e a resposta continua sendo 403; a operação protegida nunca é liberada por falha de auditoria. Isso significa que a negação continua segura, mas pode não ficar persistida se o sink estiver indisponível.

**Limites:** em modo memória, `audit_sink` é `None`, portanto não há persistência; em modo PostgreSQL, o sink existe, mas a tabela/roles continuam sem migration aplicada ou validação real. Falhas de autenticação sem principal validado não são registradas como se tivessem um ator. A mudança não registra falhas gerais de negócio nem cria uma trilha completa de segurança.

Foram acrescentados testes para confirmar o conteúdo mínimo do evento, a correlação pelo request ID e a manutenção do 403 quando a gravação falha. Os testes foram escritos, mas ainda não foram executados.


## Falhas inesperadas após autorização — preparação no código

A aplicação agora possui um handler global para exceções inesperadas. Quando a requisição passou pela dependência central de autorização, o `subject` validado fica disponível apenas no estado interno da requisição. Se o endpoint falhar depois disso, o handler tenta gravar um evento mínimo `failure` por `audit_sink.append()`, em transação separada da operação que falhou.

O evento usa ação fixa `http:unhandled_exception`, tipo `request`, resultado `failure` e o ID de requisição gerado pelo servidor. Não registra URL, parâmetros, corpo, e-mail, token, mensagem da exceção, SQL ou traceback. A resposta ao cliente é genérica (HTTP 500) e inclui somente o request ID para correlação.

Se a gravação de auditoria também falhar, a resposta permanece 500 e não expõe a exceção original. A falha de auditoria é registrada por mensagem operacional estática com request ID. Não há garantia de persistência se o sink estiver indisponível.

**Escopo:** somente falhas inesperadas de requisições que já passaram pela autorização central são associadas a um ator. Erros de validação HTTP, 401/403 e respostas HTTP tratadas não entram nessa categoria; 403 autenticado continua usando o registro `denied`. O registro de falhas não altera nem substitui o rollback das transações dos repositórios.

Testes foram adicionados para verificar evento mínimo, correlação do request ID, resposta genérica e comportamento quando o sink falha. Os testes ainda precisam ser executados; não houve validação contra PostgreSQL real.


## Validação automatizada confirmada — 27/11/2026

A execução do workflow **Bravo Shadow — testes automatizados** para o commit `59f5b90a011f6a43a35fc87b89dbcdff9999f98e` foi concluída com sucesso:

- **560 testes aprovados**, com 1 aviso de depreciação do Starlette/AnyIO.
- O job de backend utilizou PostgreSQL 16 descartável, com o banco dedicado `bravo_shadow_test` e a autorização explícita de testes destrutivos restrita ao CI.
- Os testes reais de integração cobrem a gravação conjunta de auditoria e mudança administrativa, rollback quando a auditoria falha, proteção do último Admin e concorrência entre alterações administrativas.
- O job Docker também concluiu build, inicialização do contêiner e smoke test da interface/API.

Execução: https://github.com/bravopinhais/bravopinhais/actions/runs/45982447366

**O que essa validação não significa:** o banco de produção não foi acessado; nenhuma migration foi aplicada; nenhuma role, policy ou grant foi criada; o sink PostgreSQL continua fora da composição operacional da aplicação; e as capacidades administrativas permanecem sem concessão. O PostgreSQL utilizado foi exclusivo e descartável para testes automatizados.
