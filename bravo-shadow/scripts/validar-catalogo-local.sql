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
    expected_query_indexes text[] := ARRAY[
        'formas_monetarias_created_at_idx',
        'financeiro_plano_conta_id_idx',
        'financeiro_created_at_idx',
        'moradores_bloco_apartamento_idx',
        'fornecedores_razao_social_idx',
        'empregados_nome_idx',
        'contas_bancarias_banco_idx',
        'conselheiros_nome_idx',
        'usuarios_nome_idx',
        'estoque_item_idx',
        'estoque_setor_status_idx',
        'categorias_nome_idx',
        'motivos_acerto_nome_idx',
        'documentos_categoria_id_idx',
        'documentos_created_at_idx',
        'acertos_estoque_produto_data_idx',
        'acertos_estoque_data_idx',
        'audit_events_occurred_at_idx',
        'audit_events_actor_time_idx',
        'audit_events_action_time_idx',
        'audit_events_entity_time_idx',
        'migration_batches_status_created_idx',
        'migration_batches_snapshot_idx',
        'migration_source_records_first_batch_idx',
        'migration_source_records_last_verified_idx',
        'migration_batch_recovery_history_idx',
        'migration_batch_recovery_approvals_history_idx',
        'migration_executions_batch_status_idx',
        'migration_apply_approvals_batch_idx',
        'migration_review_events_history_idx',
        'pre_import_approval_history_idx'
    ];
    missing_query_indexes text[];
    expected_check_constraints text[] := ARRAY[
        'module_settings_key_not_empty',
        'migration_batches_batch_id_nonempty',
        'migration_batches_snapshot_hash_format',
        'migration_batches_manifest_hash_format',
        'migration_batches_source_nonempty',
        'migration_batches_baseline_nonempty',
        'migration_batches_environment_allowed',
        'migration_batches_mode_allowed',
        'migration_batches_status_allowed',
        'migration_batches_versions_nonempty',
        'migration_batches_approval_complete',
        'migration_source_records_source_nonempty',
        'migration_source_records_destination_nonempty',
        'migration_source_records_hash_format',
        'migration_batch_recovery_event_id_nonempty',
        'migration_batch_recovery_sequence_positive',
        'migration_batch_recovery_outcome_allowed',
        'migration_batch_recovery_recorder_nonempty',
        'migration_batch_recovery_reviewer_nonempty',
        'migration_batch_recovery_recorder_reviewer_distinct',
        'migration_batch_recovery_rationale_nonempty',
        'migration_batch_recovery_evidence_nonempty',
        'migration_batch_recovery_evidence_hash_format',
        'migration_batch_recovery_approval_id_nonempty',
        'migration_batch_recovery_approval_actors_distinct',
        'migration_batch_recovery_approval_decision_allowed',
        'migration_batch_recovery_approval_rationale_nonempty',
        'migration_executions_id_nonempty',
        'migration_executions_subject_nonempty',
        'migration_executions_manifest_hash_format',
        'migration_executions_plan_hash_format',
        'migration_executions_environment_local_only',
        'migration_executions_status_allowed',
        'migration_executions_time_order',
        'migration_apply_approvals_id_nonempty',
        'migration_apply_approvals_reviewer_nonempty',
        'migration_apply_approvals_rationale_nonempty',
        'migration_apply_approvals_decision_allowed',
        'migration_review_batches_key_nonempty',
        'migration_review_batches_manifest_hash_format',
        'migration_review_decisions_id_nonempty',
        'migration_review_decisions_kind_nonempty',
        'migration_review_decisions_status_nonempty',
        'migration_review_decisions_manifest_hash_format',
        'migration_review_decisions_no_automatic_action',
        'migration_review_events_id_nonempty',
        'migration_review_events_reviewer_nonempty',
        'migration_review_events_rationale_nonempty',
        'migration_review_events_manifest_hash_format',
        'pre_import_approval_event_id_nonempty',
        'pre_import_approval_manifest_hash_format',
        'pre_import_approval_source_hash_format',
        'pre_import_approval_snapshot_hash_format',
        'pre_import_approval_decision_allowed',
        'pre_import_approval_scope_fixed',
        'pre_import_approval_never_authorizes_writes',
        'pre_import_approval_reviewer_nonempty',
        'pre_import_approval_rationale_nonempty',
        'pre_import_approval_sequence_positive'
    ];
    missing_check_constraints text[];
    expected_not_null_columns text[] := ARRAY[
        'migration_executions.execution_id',
        'migration_executions.batch_id',
        'migration_executions.manifest_hash',
        'migration_executions.plan_sha256',
        'migration_executions.environment',
        'migration_executions.requested_by_subject',
        'migration_executions.status',
        'migration_executions.created_at',
        'migration_apply_approvals.approval_id',
        'migration_apply_approvals.execution_id',
        'migration_apply_approvals.batch_id',
        'migration_apply_approvals.manifest_hash',
        'migration_apply_approvals.plan_sha256',
        'migration_apply_approvals.decision',
        'migration_apply_approvals.reviewer_subject',
        'migration_apply_approvals.rationale',
        'migration_apply_approvals.approved_at',
        'migration_apply_approvals.recorded_at',
        'migration_review_decisions.requires_human',
        'migration_review_decisions.automatic_action',
        'pre_import_approval_events.scope',
        'pre_import_approval_events.writes_authorized',
        'pre_import_approval_events.sequence_no',
        'pre_import_approval_events.reviewed_at',
        'pre_import_approval_events.recorded_at'
    ];
    missing_not_null_columns text[];
    expected_default_columns text[] := ARRAY[
        'migration_executions.status|prepared',
        'migration_executions.created_at|now()',
        'migration_apply_approvals.recorded_at|now()',
        'migration_review_batches.created_at|now()',
        'migration_review_decisions.requires_human|true',
        'migration_review_decisions.automatic_action|none',
        'migration_review_events.recorded_at|now()',
        'pre_import_approval_events.scope|dry_run_only',
        'pre_import_approval_events.writes_authorized|false',
        'pre_import_approval_events.recorded_at|now()'
    ];
    missing_default_columns text[];
    expected_column_types text[] := ARRAY[
        'formas_monetarias.multa_pct|double precision',
        'financeiro.valor|numeric(14,2)',
        'contas_bancarias.saldo|numeric(14,2)',
        'estoque.quantidade|numeric(14,3)',
        'estoque.minimo|numeric(14,3)',
        'estoque.maximo|numeric(14,3)',
        'estoque.valor_unitario|numeric(14,2)',
        'estoque.data_cadastro|date',
        'acertos_estoque.quantidade|numeric(14,3)',
        'acertos_estoque.data|timestamp with time zone',
        'formas_monetarias.created_at|timestamp with time zone',
        'formas_monetarias.updated_at|timestamp with time zone',
        'financeiro.created_at|timestamp with time zone',
        'financeiro.updated_at|timestamp with time zone',
        'estoque.created_at|timestamp with time zone',
        'estoque.updated_at|timestamp with time zone',
        'documentos.created_at|timestamp with time zone',
        'documentos.updated_at|timestamp with time zone',
        'audit_events.occurred_at|timestamp with time zone',
        'migration_batches.created_at|timestamp with time zone',
        'migration_source_records.created_at|timestamp with time zone',
        'migration_batch_recovery_events.reviewed_at|timestamp with time zone',
        'migration_executions.created_at|timestamp with time zone',
        'migration_apply_approvals.approved_at|timestamp with time zone',
        'migration_review_events.reviewed_at|timestamp with time zone',
        'pre_import_approval_events.reviewed_at|timestamp with time zone'
    ];
    mismatched_column_types text[];
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

    -- Confirma os índices de consulta declarados nas migrations e seu
    -- estado operacional no catálogo (válido e pronto para uso).
    SELECT array_agg(expected_name)
      INTO missing_query_indexes
      FROM unnest(expected_query_indexes) AS expected_name
     WHERE NOT EXISTS (
        SELECT 1
          FROM pg_class i
          JOIN pg_namespace n ON n.oid = i.relnamespace
          JOIN pg_index ix ON ix.indexrelid = i.oid
          JOIN pg_class t ON t.oid = ix.indrelid
         WHERE n.nspname = 'bravo_shadow'
           AND i.relname = expected_name
           AND t.relnamespace = n.oid
           AND t.relname = ANY(expected_tables)
           AND ix.indisvalid
           AND ix.indisready
     );

    IF missing_query_indexes IS NOT NULL THEN
        RAISE EXCEPTION 'Índices de consulta ausentes, inválidos ou não prontos: %',
            missing_query_indexes;
    END IF;

    -- CHECKs nomeados das migrations: todos devem existir, ser CHECK
    -- e estar validados pelo PostgreSQL.
    SELECT array_agg(expected_name)
      INTO missing_check_constraints
      FROM unnest(expected_check_constraints) AS expected_name
     WHERE NOT EXISTS (
        SELECT 1
          FROM pg_constraint
         WHERE connamespace = 'bravo_shadow'::regnamespace
           AND conname = expected_name
           AND contype = 'c'
           AND convalidated
     );

    IF missing_check_constraints IS NOT NULL THEN
        RAISE EXCEPTION 'CHECKs ausentes ou não validados: %',
            missing_check_constraints;
    END IF;

    -- NOT NULL nos campos de identidade, estado e auditoria mais sensíveis.
    SELECT array_agg(expected_column)
      INTO missing_not_null_columns
      FROM unnest(expected_not_null_columns) AS expected_column
     WHERE NOT EXISTS (
        SELECT 1
          FROM pg_attribute att
          JOIN pg_class tbl ON tbl.oid = att.attrelid
          JOIN pg_namespace ns ON ns.oid = tbl.relnamespace
         WHERE ns.nspname = 'bravo_shadow'
           AND tbl.relname = split_part(expected_column, '.', 1)
           AND att.attname = split_part(expected_column, '.', 2)
           AND att.attnum > 0
           AND NOT att.attisdropped
           AND att.attnotnull
     );

    IF missing_not_null_columns IS NOT NULL THEN
        RAISE EXCEPTION 'Colunas críticas sem NOT NULL: %',
            missing_not_null_columns;
    END IF;

    -- DEFAULTs críticos: exige expressão cadastrada e que contenha o
    -- literal/expressão esperado, sem impor formatação textual exata.
    SELECT array_agg(expected_column)
      INTO missing_default_columns
      FROM unnest(expected_default_columns) AS expected_column
     WHERE NOT EXISTS (
        SELECT 1
          FROM pg_attribute att
          JOIN pg_class tbl ON tbl.oid = att.attrelid
          JOIN pg_namespace ns ON ns.oid = tbl.relnamespace
          JOIN pg_attrdef def ON def.adrelid = tbl.oid
                             AND def.adnum = att.attnum
         WHERE ns.nspname = 'bravo_shadow'
           AND tbl.relname = split_part(expected_column, '.', 1)
           AND att.attname = split_part(split_part(expected_column, '.', 2), '|', 1)
           AND att.attnum > 0
           AND NOT att.attisdropped
           AND pg_get_expr(def.adbin, def.adrelid) ILIKE
               '%' || split_part(expected_column, '|', 2) || '%'
     );

    IF missing_default_columns IS NOT NULL THEN
        RAISE EXCEPTION 'DEFAULTs críticos ausentes ou divergentes: %',
            missing_default_columns;
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

    -- Confere tipos e precisão dos campos numéricos, datas e timestamps
    -- que fazem parte dos contratos de payload e trilha de auditoria.
    SELECT array_agg(expected_column || ' esperado=' || expected_type)
      INTO mismatched_column_types
      FROM (
        SELECT split_part(item, '|', 1) AS expected_column,
               split_part(item, '|', 2) AS expected_type
          FROM unnest(expected_column_types) AS item
      ) expected
     WHERE NOT EXISTS (
        SELECT 1
          FROM pg_attribute att
          JOIN pg_class tbl ON tbl.oid = att.attrelid
          JOIN pg_namespace ns ON ns.oid = tbl.relnamespace
         WHERE ns.nspname = 'bravo_shadow'
           AND tbl.relname = split_part(expected.expected_column, '.', 1)
           AND att.attname = split_part(expected.expected_column, '.', 2)
           AND att.attnum > 0
           AND NOT att.attisdropped
           AND format_type(att.atttypid, att.atttypmod) = expected.expected_type
     );

    IF mismatched_column_types IS NOT NULL THEN
        RAISE EXCEPTION 'Tipos/precisões de colunas divergentes: %',
            mismatched_column_types;
    END IF;

    RAISE NOTICE 'OK: % tabelas, % FKs, % CHECKs nomeados, % NOT NULLs, % DEFAULTs, % tipos/precisões, % índices únicos e % índices de consulta verificados; RLS e controles de acesso conferidos.',
        cardinality(expected_tables), cardinality(expected_foreign_keys),
        cardinality(expected_check_constraints), cardinality(expected_not_null_columns),
        cardinality(expected_default_columns), cardinality(expected_column_types),
        cardinality(expected_unique_indexes), cardinality(expected_query_indexes);
END;
$$;
