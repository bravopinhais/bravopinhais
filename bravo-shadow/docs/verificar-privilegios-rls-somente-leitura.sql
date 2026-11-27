-- Bravo Shadow: inspeção somente leitura de roles, privilégios e RLS.
-- Executar APENAS em PostgreSQL local descartável ou ambiente formalmente autorizado.
-- Este arquivo não cria roles, schemas, tabelas, grants, policies ou migrations.
-- Não contém dados de negócio; retorna apenas metadados do catálogo.
-- Compatível com PostgreSQL 16.
BEGIN READ ONLY;

-- 1. Contexto da conexão e versão do servidor.
SELECT current_database() AS database_name,
       session_user AS session_role,
       current_user AS effective_role,
       current_setting('server_version') AS server_version;

-- 2. Atributos de todas as roles.
SELECT rolname, rolsuper, rolinherit, rolcreaterole, rolcreatedb,
       rolcanlogin, rolreplication, rolbypassrls
FROM pg_roles
ORDER BY rolname;

-- 3. Memberships efetivas, inclusive caminhos transitivos conhecidos pelo servidor.
SELECT member.rolname AS member_role,
       target.rolname AS target_role,
       pg_has_role(member.oid, target.oid, 'MEMBER') AS is_member,
       pg_has_role(member.oid, target.oid, 'USAGE') AS inherits_privileges,
       pg_has_role(member.oid, target.oid, 'SET') AS can_set_role
FROM pg_roles AS member
CROSS JOIN pg_roles AS target
WHERE member.oid <> target.oid
  AND pg_has_role(member.oid, target.oid, 'MEMBER')
ORDER BY member.rolname, target.rolname;

-- 4. Ownership e flags de RLS em tabelas do schema Bravo Shadow.
SELECT n.nspname AS schema_name,
       c.relname AS object_name,
       owner.rolname AS object_owner,
       c.relkind AS object_kind,
       c.relrowsecurity AS rls_enabled,
       c.relforcerowsecurity AS rls_forced
FROM pg_class AS c
JOIN pg_namespace AS n ON n.oid = c.relnamespace
JOIN pg_roles AS owner ON owner.oid = c.relowner
WHERE n.nspname = 'bravo_shadow'
  AND c.relkind IN ('r', 'p')
ORDER BY c.relname;

-- 5. Policies efetivamente cadastradas no schema.
SELECT schemaname, tablename, policyname, permissive,
       roles, cmd, qual, with_check
FROM pg_policies
WHERE schemaname = 'bravo_shadow'
ORDER BY tablename, policyname;

-- 6. Privilégios efetivos de cada role sobre cada tabela.
-- Inclui efeitos de ownership e memberships reconhecidos pelo PostgreSQL.
SELECT r.rolname AS role_name,
       c.relname AS table_name,
       has_table_privilege(r.oid, c.oid, 'SELECT') AS can_select,
       has_table_privilege(r.oid, c.oid, 'INSERT') AS can_insert,
       has_table_privilege(r.oid, c.oid, 'UPDATE') AS can_update,
       has_table_privilege(r.oid, c.oid, 'DELETE') AS can_delete,
       has_table_privilege(r.oid, c.oid, 'TRUNCATE') AS can_truncate,
       has_table_privilege(r.oid, c.oid, 'REFERENCES') AS can_reference,
       has_table_privilege(r.oid, c.oid, 'TRIGGER') AS can_trigger
FROM pg_roles AS r
CROSS JOIN pg_class AS c
JOIN pg_namespace AS n ON n.oid = c.relnamespace
WHERE n.nspname = 'bravo_shadow'
  AND c.relkind IN ('r', 'p')
ORDER BY r.rolname, c.relname;

-- 7. Privilégios efetivos no schema.
SELECT r.rolname AS role_name,
       has_schema_privilege(r.oid, n.oid, 'USAGE') AS can_use_schema,
       has_schema_privilege(r.oid, n.oid, 'CREATE') AS can_create_in_schema
FROM pg_roles AS r
CROSS JOIN pg_namespace AS n
WHERE n.nspname = 'bravo_shadow'
ORDER BY r.rolname;

-- 8. Privilégios efetivos sobre sequences do schema.
SELECT r.rolname AS role_name,
       c.relname AS sequence_name,
       has_sequence_privilege(r.oid, c.oid, 'USAGE') AS can_use,
       has_sequence_privilege(r.oid, c.oid, 'SELECT') AS can_select,
       has_sequence_privilege(r.oid, c.oid, 'UPDATE') AS can_update
FROM pg_roles AS r
CROSS JOIN pg_class AS c
JOIN pg_namespace AS n ON n.oid = c.relnamespace
WHERE n.nspname = 'bravo_shadow'
  AND c.relkind = 'S'
ORDER BY r.rolname, c.relname;

-- 9. Privilégio EXECUTE efetivo sobre funções do schema.
SELECT r.rolname AS role_name,
       p.proname AS function_name,
       pg_get_function_identity_arguments(p.oid) AS arguments,
       has_function_privilege(r.oid, p.oid, 'EXECUTE') AS can_execute
FROM pg_roles AS r
CROSS JOIN pg_proc AS p
JOIN pg_namespace AS n ON n.oid = p.pronamespace
WHERE n.nspname = 'bravo_shadow'
ORDER BY r.rolname, p.proname, arguments;

-- 10. ACL explícita do schema, para comparar com os privilégios efetivos.
SELECT n.nspname AS schema_name,
       CASE WHEN acl.grantee = 0 THEN 'PUBLIC' ELSE grantee.rolname END AS grantee,
       acl.privilege_type,
       acl.is_grantable
FROM pg_namespace AS n
CROSS JOIN LATERAL aclexplode(
    COALESCE(n.nspacl, acldefault('n', n.nspowner))
) AS acl
LEFT JOIN pg_roles AS grantee ON grantee.oid = acl.grantee
WHERE n.nspname = 'bravo_shadow'
ORDER BY grantee, acl.privilege_type;

-- Encerramento sem escrita.
COMMIT;
