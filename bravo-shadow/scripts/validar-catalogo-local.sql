-- Auditoria READ-ONLY do catálogo PostgreSQL após supabase db reset --local.
-- Executar somente contra a stack local descartável do Bravo Shadow.
-- Não lê linhas de negócio, não altera schema e não concede privilégios.

DO $$
DECLARE
    expected_tables text[] := ARRAY[
        'formas_monetarias', 'plano_contas', 'financeiro', 'moradores',
        'fornecedores', 'empregados', 'contas_bancarias', 'condominio',
        'conselheiros', 'usuarios', 'estoque', 'categorias', 'motivos_acerto',
        'documentos', 'acertos_estoque', 'module_settings', 'audit_events',
        'migration_batches', 'migration_source_records',
        'migration_batch_recovery_events', 'migration_batch_recovery_approvals',
        'migration_executions', 'migration_apply_approvals',
        'migration_review_batches', 'migration_review_decisions',
        'migration_review_events', 'pre_import_approval_events'
    ];
    table_name text;
    relation_oid oid;
    role_name text;
    expected_roles text[] := ARRAY['anon', 'authenticated', 'service_role'];
    expected_foreign_keys text[] := ARRAY[
        'financeiro_plano_conta_fk',
        'documentos_categoria_fk',
        'acertos_estoque_produto_fk',
        'acertos_estoque_motivo_fk',
        'migration_source_records_first_batch_fk',
        'migration_source_records_last_batch_fk',
        'migration_batch_recovery_manifest_fk',
        'migration_batch_recovery_source_fk',
        'migration_batch_recovery_approval_actor_binding_fk',
        'migration_executions_batch_manifest_fk',
        'migration_apply_approvals_execution_fk',
        'migration_review_decisions_batch_manifest_fk',
        'migration_review_events_decision_manifest_fk'
    ];
    missing_foreign_keys text[];
    expected_unique_indexes text[] := ARRAY[
        'plano_contas_codigo_ci_uidx',
        'usuarios_email_ci_uidx',
        'migration_batches_id_manifest_unique',
        'migration_batches_id_source_unique',
        'migration_source_records_destination_unique',
        'migration_batch_recovery_sequence_unique',
        'migration_batch_recovery_approval_binding_unique',
        'migration_batch_recovery_approval_event_unique',
        'migration_executions_batch_plan_unique',
        'migration_executions_full_identity_unique',
        'migration_apply_approvals_one_decision_per_execution',
        'migration_review_batches_key_manifest_unique',
        'migration_review_decisions_batch_decision_manifest_unique',
        'migration_review_events_version_unique',
        'pre_import_approval_manifest_sequence_unique'
    ];
    missing_unique_indexes text[];
    missing_roles text[];
    missing_tables text[];
    bad_tables text[];
    policy_tables text[];
    granted_tables text[];
    has_append_only_triggers boolean;
    has_forced_audit_rls boolean;
    has_no_write_constraint boolean;
    has_dry_run_constraint boolean;
BEGIN
    SELECT array_agg(r)
      INTO missing_roles
      FROM unnest(expected_roles) AS r
     WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r);

    IF missing_roles IS NOT NULL THEN
        RAISE EXCEPTION 'Roles Supabase ausentes: %', missing_roles;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = 'bravo_shadow') THEN
        RAISE EXCEPTION 'Schema bravo_shadow ausente.';
    END IF;

    SELECT array_agg(t)
      INTO missing_tables
      FROM unnest(expected_tables) AS t
     WHERE to_regclass(format('bravo_shadow.%I', t)) IS NULL;

    IF missing_tables IS NOT NULL THEN
        RAISE EXCEPTION 'Tabelas ausentes: %', missing_tables;
    END IF;

    SELECT array_agg(expected_name)
      INTO missing_foreign_keys
      FROM unnest(expected_foreign_keys) AS expected_name
     WHERE NOT EXISTS (
        SELECT 1
          FROM pg_constraint
         WHERE conname = expected_name
           AND contype = 'f'
           AND convalidated
           AND connamespace = 'bravo_shadow'::regnamespace
     );

    IF missing_foreign_keys IS NOT NULL THEN
        RAISE EXCEPTION 'FKs ausentes ou não validadas: %', missing_foreign_keys;
    END IF;

    -- Verifica índices que implementam unicidade, inclusive índices
    -- funcionais (lower/btrim) e índices criados por constraints UNIQUE.
    SELECT array_agg(expected_name)
      INTO missing_unique_indexes
      FROM unnest(expected_unique_indexes) AS expected_name
     WHERE NOT EXISTS (
        SELECT 1
          FROM pg_class i
          JOIN pg_namespace n ON n.oid = i.relnamespace
          JOIN pg_index ix ON ix.indexrelid = i.oid
         WHERE n.nspname = 'bravo_shadow'
           AND i.relname = expected_name
           AND ix.indisunique
           AND ix.indisvalid
           AND ix.indisready
     );

    IF missing_unique_indexes IS NOT NULL THEN
        RAISE EXCEPTION 'Índices únicos ausentes, inválidos ou não prontos: %',
            missing_unique_indexes;
    END IF;

    FOREACH table_name IN ARRAY expected_tables LOOP
        relation_oid := to_regclass(format('bravo_shadow.%I', table_name));

        IF NOT (SELECT relrowsecurity FROM pg_class WHERE oid = relation_oid) THEN
            RAISE EXCEPTION 'RLS não está habilitado em bravo_shadow.%', table_name;
        END IF;

        FOREACH role_name IN ARRAY expected_roles LOOP
            IF has_table_privilege(role_name, relation_oid, 'SELECT')
               OR has_table_privilege(role_name, relation_oid, 'INSERT')
               OR has_table_privilege(role_name, relation_oid, 'UPDATE')
               OR has_table_privilege(role_name, relation_oid, 'DELETE')
               OR has_table_privilege(role_name, relation_oid, 'TRUNCATE')
               OR has_table_privilege(role_name, relation_oid, 'REFERENCES')
               OR has_table_privilege(role_name, relation_oid, 'TRIGGER') THEN
                RAISE EXCEPTION 'Privilégio inesperado para role % em bravo_shadow.%',
                    role_name, table_name;
            END IF;
        END LOOP;
    END LOOP;

    IF has_schema_privilege('anon', 'bravo_shadow', 'USAGE')
       OR has_schema_privilege('anon', 'bravo_shadow', 'CREATE')
       OR has_schema_privilege('authenticated', 'bravo_shadow', 'USAGE')
       OR has_schema_privilege('authenticated', 'bravo_shadow', 'CREATE')
       OR has_schema_privilege('service_role', 'bravo_shadow', 'USAGE')
       OR has_schema_privilege('service_role', 'bravo_shadow', 'CREATE') THEN
        RAISE EXCEPTION 'Privilégio inesperado no schema bravo_shadow.';
    END IF;

    SELECT array_agg(c.relname)
      INTO policy_tables
      FROM pg_class c
      JOIN pg_namespace n ON n.oid = c.relnamespace
      JOIN pg_policies p ON p.schemaname = n.nspname AND p.tablename = c.relname
     WHERE n.nspname = 'bravo_shadow'
       AND c.relname = ANY(expected_tables);

    IF policy_tables IS NOT NULL THEN
        RAISE EXCEPTION 'Policies inesperadas nesta fase: %', policy_tables;
    END IF;

    SELECT relforcerowsecurity
      INTO has_forced_audit_rls
      FROM pg_class
     WHERE oid = 'bravo_shadow.audit_events'::regclass;

    IF NOT has_forced_audit_rls THEN
        RAISE EXCEPTION 'FORCE ROW LEVEL SECURITY ausente em audit_events.';
    END IF;

    SELECT
        count(*) FILTER (WHERE tgname = 'pre_import_approval_no_update_delete'
                         AND tgenabled <> 'D') = 1
        AND
        count(*) FILTER (WHERE tgname = 'pre_import_approval_no_truncate'
                         AND tgenabled <> 'D') = 1
      INTO has_append_only_triggers
      FROM pg_trigger
     WHERE tgrelid = 'bravo_shadow.pre_import_approval_events'::regclass
       AND NOT tgisinternal;

    IF NOT has_append_only_triggers THEN
        RAISE EXCEPTION 'Triggers append-only da aprovação pré-importação ausentes/desabilitados.';
    END IF;

    SELECT EXISTS (
        SELECT 1 FROM pg_constraint
         WHERE conrelid = 'bravo_shadow.pre_import_approval_events'::regclass
           AND conname = 'pre_import_approval_never_authorizes_writes'
           AND convalidated
    ) INTO has_no_write_constraint;

    SELECT EXISTS (
        SELECT 1 FROM pg_constraint
         WHERE conrelid = 'bravo_shadow.pre_import_approval_events'::regclass
           AND conname = 'pre_import_approval_scope_fixed'
           AND convalidated
    ) INTO has_dry_run_constraint;

    IF NOT has_no_write_constraint OR NOT has_dry_run_constraint THEN
        RAISE EXCEPTION 'Restrições de aprovação exclusivamente dry-run ausentes/não validadas.';
    END IF;

    RAISE NOTICE 'OK: % tabelas, % FKs e % índices únicos presentes/válidos; RLS habilitado; sem policies ou grants às roles comuns; auditoria e aprovação pré-importação verificadas.',
        cardinality(expected_tables), cardinality(expected_foreign_keys),
        cardinality(expected_unique_indexes);
END;
$$;
