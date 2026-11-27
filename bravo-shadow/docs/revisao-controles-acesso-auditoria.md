# Revisão de controles de acesso — auditoria PostgreSQL

**Data:** 27/11/2026  
**Escopo:** revisão estática do rascunho `docs/sql-auditoria-rascunho.sql`, do adaptador Python e dos contratos de autorização.  
**Natureza:** análise documental; não executa SQL, não conecta banco e não altera privilégios.

## Resultado

**Apto para continuar em ambiente local descartável, mas não apto para produção ou conexão operacional.**

O rascunho aplica `ENABLE ROW LEVEL SECURITY` e `FORCE ROW LEVEL SECURITY` à tabela proposta e revoga privilégios de `PUBLIC`, `anon`, `authenticated` e `service_role`. Não há concessão para uma role writer ou reader dedicada, nem policies de leitura. Portanto, o desenho atual é deliberadamente fechado: ainda não permite que a API grave nem que um operador consulte a auditoria.

## Matriz de acesso revisada

| Identidade | Acesso pretendido | Estado atual |
|---|---|---|
| Owner/migration | DDL e migrations fora da API | Conceito documentado; role não criada |
| Writer/API | Somente INSERT | Conceito documentado; sem role, grant ou membership |
| Reader/auditoria | SELECT restrito | Conceito documentado; sem role, grant, policy ou rota |
| PUBLIC / anon / authenticated / service_role | Nenhum acesso concedido pelo rascunho | REVOKE ALL explícito no SQL proposto; não aplicado |

## Controles que devem ser provados localmente

1. Confirmar que nenhuma role da API tem `SUPERUSER`, `BYPASSRLS`, ownership da tabela ou privilégios herdados que contornem RLS.
2. Confirmar memberships efetivas e privilégios herdados, não apenas grants diretos.
3. Confirmar que writer pode executar INSERT e não pode SELECT, UPDATE, DELETE, TRUNCATE ou DDL.
4. Confirmar que reader pode executar somente SELECT conforme escopo aprovado e não pode inserir, editar ou apagar.
5. Confirmar que `PUBLIC`, `anon`, `authenticated` e `service_role` não conseguem ler nem modificar a tabela.
6. Confirmar que owner/migration não é usado pela aplicação e que credenciais administrativas não são expostas ao frontend.
7. Confirmar que nenhuma policy permissiva (`USING (true)` / `WITH CHECK (true)`) foi introduzida para contornar o bloqueio.
8. Testar os privilégios com `SET ROLE` e consultas efetivas no PostgreSQL local descartável; registrar os resultados sem dados reais.

## Observações técnicas

- RLS não substitui privilégios SQL: os grants devem ser mínimos e testados em conjunto com as policies.
- `FORCE ROW LEVEL SECURITY` sujeita o owner às policies em operações normais, mas não neutraliza superusers ou roles com `BYPASSRLS`.
- `REVOKE` no rascunho é apenas texto versionado; não altera qualquer banco até uma migration ser criada e aplicada.
- O adaptador `PostgresAuditSink` oferece somente INSERT no nível da aplicação. Isso não é uma barreira de segurança suficiente se a credencial PostgreSQL possuir privilégios maiores.
- A consulta de auditoria ainda não possui endpoint nem capacidade concedida. Não criar uma rota de leitura antes de aprovar o modelo de acesso.
- A matriz `ROLE_CAPABILITIES` continua vazia para Admin e Operador. Esta revisão não recomenda nem concede permissões funcionais.

## Pendências antes de qualquer integração

- Definir nomes reais das roles e seus memberships na stack local.
- Definir o escopo de leitura e a capacidade específica para consulta de auditoria.
- Definir retenção, backup, restauração e monitoramento.
- Gerar migration por ferramenta apropriada somente após revisão do desenho.
- Aplicar e testar apenas em PostgreSQL local descartável, com dados sintéticos.
- Fazer revisão independente dos resultados e obter autorização explícita antes de qualquer ambiente compartilhado ou produção.

## Limites desta revisão

Nenhuma migration foi criada ou aplicada. Nenhuma role, policy, grant, membership, segredo ou variável de ambiente foi criada ou alterada. Nenhum banco foi acessado. O login Google, a interface original, a matriz de permissões e o fluxo de produção permanecem inalterados.

## Evidência automatizada complementar — 27/11/2026

O commit `96e4b47152b0167b2ac9bf056cff103c6b158767` acrescentou dois testes de contrato para o rascunho de auditoria: confirmação de RLS habilitado/forçado e revogações explícitas, além da ausência de GRANT e policies no texto SQL.

A execução GitHub Actions `45983529674` concluiu os trabalhos Backend e Docker com sucesso. O backend reportou **562 testes aprovados, 1 aviso de depreciação e nenhuma falha**. O trabalho Docker concluiu construção, inicialização do contêiner e smoke test de interface/API.

Esta evidência valida os contratos automatizados do repositório e o comportamento do contêiner de demonstração. **Não** comprova privilégios efetivos em um banco compartilhado, não aplica o rascunho SQL e não autoriza integração operacional ou produção. A revisão de roles, memberships, grants e policies ainda depende de execução controlada em PostgreSQL local descartável.


## Revalidação após correção das expressões regulares — 27/11/2026

O commit `79631f3620972e58753ff873886b82f522bec04c` corrigiu as expressões regulares usadas pelos testes estáticos para remover comentários SQL e detectar comandos `GRANT` e `CREATE POLICY`. A execução GitHub Actions `45986569334` concluiu ambos os trabalhos com sucesso: **562 testes aprovados, 1 aviso de depreciação e nenhuma falha** no backend; construção da imagem Docker, inicialização do contêiner e smoke test de interface/API também aprovados.

O aviso restante vem do alias `anyio.abc.BlockingPortal` usado pelo `starlette.testclient`; não causou falha nesta execução. Os erros “forced integration rollback”, “forced deferred commit failure”, “forced audit failure” e “forced deactivation audit failure” aparecem nos logs como cenários intencionais dos testes de falha/rollback, não como falhas da suíte.

Esta revalidação confirma a correção dos testes e o estado da suíte automatizada. Continua sem executar o rascunho SQL, criar roles/policies/grants ou acessar banco compartilhado/produção.


## Roteiro de inspeção somente leitura — PostgreSQL local descartável

Este roteiro complementa a especificação de RLS existente. As consultas abaixo são exclusivamente de catálogo (SELECT): não criam roles, não alteram grants e não aplicam policies. Executar somente depois de existir uma instância PostgreSQL local descartável e uma migration previamente revisada. Não apontar para Supabase hospedado, produção ou banco compartilhado.

### 1. Atributos de roles

~~~sql
SELECT rolname, rolsuper, rolinherit, rolcreaterole, rolcreatedb,
       rolcanlogin, rolreplication, rolbypassrls
FROM pg_roles
ORDER BY rolname;
~~~

Critério: a identidade runtime não pode ser superuser, possuir BYPASSRLS, CREATEDB ou CREATEROLE. Registrar também se pode fazer login e se herda memberships.

### 2. Memberships e caminhos de herança

~~~sql
SELECT member.rolname AS member_role,
       granted.rolname AS granted_role,
       m.admin_option,
       pg_has_role(member.oid, granted.oid, 'MEMBER') AS is_member,
       pg_has_role(member.oid, granted.oid, 'USAGE') AS inherits_privileges
FROM pg_auth_members AS m
JOIN pg_roles AS member ON member.oid = m.member
JOIN pg_roles AS granted ON granted.oid = m.roleid
ORDER BY member.rolname, granted.rolname;
~~~

Critério: nenhuma membership runtime pode levar, direta ou indiretamente, a owner, migrator, superuser ou role com BYPASSRLS. Investigar todo caminho transitivo, não apenas associação direta.

### 3. Ownership, RLS e policies do schema privado

~~~sql
SELECT n.nspname AS schema_name,
       c.relname AS table_name,
       owner.rolname AS table_owner,
       c.relrowsecurity AS rls_enabled,
       c.relforcerowsecurity AS rls_forced
FROM pg_class AS c
JOIN pg_namespace AS n ON n.oid = c.relnamespace
JOIN pg_roles AS owner ON owner.oid = c.relowner
WHERE n.nspname = 'bravo_shadow'
  AND c.relkind IN ('r', 'p')
ORDER BY c.relname;

SELECT schemaname, tablename, policyname, permissive,
       roles, cmd, qual, with_check
FROM pg_policies
WHERE schemaname = 'bravo_shadow'
ORDER BY tablename, policyname;
~~~

Critério: conferir tabela por tabela. Policies devem nomear explicitamente as roles aprovadas; qualquer policy PUBLIC, condição ampla ou expressão inesperada bloqueia a homologação até revisão.

### 4. Grants explícitos e privilégios efetivos

~~~sql
SELECT grantee, table_schema, table_name, privilege_type, is_grantable
FROM information_schema.role_table_grants
WHERE table_schema = 'bravo_shadow'
ORDER BY table_name, grantee, privilege_type;

SELECT n.nspname AS schema_name,
       r.rolname AS role_name,
       has_schema_privilege(r.oid, n.oid, 'USAGE') AS can_use_schema,
       has_schema_privilege(r.oid, n.oid, 'CREATE') AS can_create_in_schema
FROM pg_namespace AS n
CROSS JOIN pg_roles AS r
WHERE n.nspname = 'bravo_shadow'
ORDER BY r.rolname;
~~~

Critério: avaliar privilégios efetivos e herdados para cada identidade aprovada. Não concluir segurança apenas pela ausência de grants diretos; considerar memberships, ownership, privilégios de PUBLIC, sequences e funções.

### 5. Checklist de operações negativas e positivas

Após os nomes e grants serem aprovados, conectar-se usando credenciais independentes de cada role (não usar apenas SET ROLE a partir de superuser) e testar com dados sintéticos em transações descartáveis:

- runtime: SELECT apenas nas tabelas aprovadas; INSERT somente nas tabelas aprovadas; UPDATE/DELETE/TRUNCATE/DDL negados onde não previstos;
- writer de auditoria: INSERT permitido somente se esse desenho for aprovado; SELECT/UPDATE/DELETE/TRUNCATE/DDL negados;
- reader de auditoria: SELECT limitado ao escopo aprovado; toda escrita negada;
- anon, authenticated, service_role e PUBLIC: sem acesso ao schema privado;
- role migrator/owner: validar separadamente o comportamento de FORCE ROW LEVEL SECURITY, sem reutilizar sua credencial na API.

Não executar testes destrutivos em uma instância que contenha qualquer dado não descartável. A transação ROLLBACK é uma proteção adicional, não substitui o isolamento da instância. Não incluir senha, token ou string de conexão em logs ou documentação.

### 6. Evidência e critério de saída

Guardar versão PostgreSQL, commit da migration testada, comandos executados, resultados de catálogo e resultados de cada tentativa permitida/negada. O aceite exige revisão independente da matriz completa e ausência de privilégios indiretos inesperados. Até lá, o SQL permanece rascunho e a integração PostgreSQL continua bloqueada.
