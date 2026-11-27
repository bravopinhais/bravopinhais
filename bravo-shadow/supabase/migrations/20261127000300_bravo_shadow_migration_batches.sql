-- Bravo Shadow versioned migration.
-- Source draft: sql-controle-lotes-importacao-rascunho.sql.
-- Promoted to versioned history for disposable/local review only.
-- No production execution or import authorization is implied.


CREATE SCHEMA IF NOT EXISTS bravo_shadow;

-- batch_id é determinístico sobre snapshot + versões do envelope, manifesto,
-- canonicalização, importador e mapeamento; nova lógica gera novo lote.
CREATE TABLE IF NOT EXISTS bravo_shadow.migration_batches (
    batch_id text PRIMARY KEY,
    snapshot_hash text NOT NULL,
    manifest_hash text NOT NULL,
    source_system text NOT NULL,
    source_baseline text NOT NULL,
    environment text NOT NULL,
    mode text NOT NULL,
    status text NOT NULL DEFAULT 'prepared',
    importer_version text NOT NULL,
    mapping_version text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    finished_at timestamptz NULL,
    approved_by text NULL,
    approved_at timestamptz NULL,
    approved_manifest_hash text NULL,

    CONSTRAINT migration_batches_batch_id_nonempty
        CHECK (length(btrim(batch_id)) > 0),
    CONSTRAINT migration_batches_snapshot_hash_format
        CHECK (snapshot_hash ~ '^[0-9a-f]{64}$'),
    CONSTRAINT migration_batches_manifest_hash_format
        CHECK (manifest_hash ~ '^[0-9a-f]{64}$'),
    CONSTRAINT migration_batches_source_nonempty
        CHECK (length(btrim(source_system)) > 0),
    CONSTRAINT migration_batches_baseline_nonempty
        CHECK (length(btrim(source_baseline)) > 0),
    CONSTRAINT migration_batches_environment_allowed
        CHECK (environment IN ('local_disposable', 'ci_ephemeral')),
    CONSTRAINT migration_batches_mode_allowed
        CHECK (mode IN ('inspect', 'dry_run', 'apply', 'verify', 'rollback')),
    CONSTRAINT migration_batches_status_allowed
        CHECK (status IN (
            'prepared', 'approved', 'applying', 'applied',
            'verified', 'failed', 'rolled_back', 'needs_review'
        )),
    CONSTRAINT migration_batches_versions_nonempty
        CHECK (
            length(btrim(importer_version)) > 0
            AND length(btrim(mapping_version)) > 0
        ),
    CONSTRAINT migration_batches_approval_complete
        CHECK (
            (approved_by IS NULL AND approved_at IS NULL AND approved_manifest_hash IS NULL)
            OR
            (
                length(btrim(approved_by)) > 0
                AND approved_at IS NOT NULL
                AND approved_manifest_hash = manifest_hash
            )
        ),
    CONSTRAINT migration_batches_id_manifest_unique
        UNIQUE (batch_id, manifest_hash),
    CONSTRAINT migration_batches_id_source_unique
        UNIQUE (batch_id, source_system)
);

CREATE INDEX IF NOT EXISTS migration_batches_status_created_idx
    ON bravo_shadow.migration_batches (status, created_at DESC);

CREATE INDEX IF NOT EXISTS migration_batches_snapshot_idx
    ON bravo_shadow.migration_batches (source_system, snapshot_hash);

-- Não armazena payload de origem nem dados pessoais: somente identidade,
-- hash e endereço lógico do registro de destino.
CREATE TABLE IF NOT EXISTS bravo_shadow.migration_source_records (
    source_system text NOT NULL,
    source_collection text NOT NULL,
    legacy_id text NOT NULL,
    destination_collection text NOT NULL,
    destination_id text NOT NULL,
    source_record_hash text NOT NULL,
    first_batch_id text NOT NULL,
    last_verified_batch_id text NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT migration_source_records_pk
        PRIMARY KEY (source_system, source_collection, legacy_id),
    CONSTRAINT migration_source_records_source_nonempty
        CHECK (
            length(btrim(source_system)) > 0
            AND length(btrim(source_collection)) > 0
            AND length(btrim(legacy_id)) > 0
        ),
    CONSTRAINT migration_source_records_destination_nonempty
        CHECK (
            length(btrim(destination_collection)) > 0
            AND length(btrim(destination_id)) > 0
        ),
    CONSTRAINT migration_source_records_hash_format
        CHECK (source_record_hash ~ '^[0-9a-f]{64}$'),
    CONSTRAINT migration_source_records_first_batch_fk
        FOREIGN KEY (first_batch_id, source_system)
        REFERENCES bravo_shadow.migration_batches(batch_id, source_system)
        ON DELETE RESTRICT,
    CONSTRAINT migration_source_records_last_batch_fk
        FOREIGN KEY (last_verified_batch_id, source_system)
        REFERENCES bravo_shadow.migration_batches(batch_id, source_system)
        ON DELETE RESTRICT,
    CONSTRAINT migration_source_records_destination_unique
        UNIQUE (destination_collection, destination_id)
);

CREATE INDEX IF NOT EXISTS migration_source_records_first_batch_idx
    ON bravo_shadow.migration_source_records (first_batch_id);

CREATE INDEX IF NOT EXISTS migration_source_records_last_verified_idx
    ON bravo_shadow.migration_source_records (last_verified_batch_id)
    WHERE last_verified_batch_id IS NOT NULL;

-- Decisão humana sobre lote interrompido. Este histórico não reabre o lote,
-- não altera status e não autoriza reaplicação; apenas registra evidência.
CREATE TABLE IF NOT EXISTS bravo_shadow.migration_batch_recovery_events (
    event_id text PRIMARY KEY,
    batch_id text NOT NULL,
    source_system text NOT NULL,
    manifest_hash text NOT NULL,
    sequence_no integer NOT NULL,
    outcome text NOT NULL,
    recorded_by text NOT NULL,
    reviewer_id text NOT NULL,
    rationale text NOT NULL,
    evidence_reference text NOT NULL,
    evidence_sha256 text NOT NULL,
    reviewed_at timestamptz NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT migration_batch_recovery_event_id_nonempty
        CHECK (length(btrim(event_id)) > 0),
    CONSTRAINT migration_batch_recovery_sequence_positive
        CHECK (sequence_no > 0),
    CONSTRAINT migration_batch_recovery_outcome_allowed
        CHECK (outcome IN (
            'confirmed_committed',
            'confirmed_not_committed',
            'partial_or_unknown',
            'rollback_verified'
        )),
    CONSTRAINT migration_batch_recovery_recorder_nonempty
        CHECK (length(btrim(recorded_by)) > 0),
    CONSTRAINT migration_batch_recovery_reviewer_nonempty
        CHECK (length(btrim(reviewer_id)) > 0),
    CONSTRAINT migration_batch_recovery_recorder_reviewer_distinct
        CHECK (recorded_by <> reviewer_id),
    CONSTRAINT migration_batch_recovery_rationale_nonempty
        CHECK (length(btrim(rationale)) > 0),
    CONSTRAINT migration_batch_recovery_evidence_nonempty
        CHECK (length(btrim(evidence_reference)) > 0),
    CONSTRAINT migration_batch_recovery_evidence_hash_format
        CHECK (evidence_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT migration_batch_recovery_manifest_fk
        FOREIGN KEY (batch_id, manifest_hash)
        REFERENCES bravo_shadow.migration_batches(batch_id, manifest_hash)
        ON DELETE RESTRICT,
    CONSTRAINT migration_batch_recovery_source_fk
        FOREIGN KEY (batch_id, source_system)
        REFERENCES bravo_shadow.migration_batches(batch_id, source_system)
        ON DELETE RESTRICT,
    CONSTRAINT migration_batch_recovery_sequence_unique
        UNIQUE (batch_id, sequence_no),
    CONSTRAINT migration_batch_recovery_approval_binding_unique
        UNIQUE (event_id, recorded_by, reviewer_id)
);

CREATE INDEX IF NOT EXISTS migration_batch_recovery_history_idx
    ON bravo_shadow.migration_batch_recovery_events (batch_id, sequence_no);

-- Aprovação independente: um segundo ator confirma ou rejeita o evento.
-- A aprovação também é append-only; uma rejeição exige novo evento de recovery.
CREATE TABLE IF NOT EXISTS bravo_shadow.migration_batch_recovery_approvals (
    approval_id text PRIMARY KEY,
    event_id text NOT NULL,
    recorded_by text NOT NULL,
    reviewer_id text NOT NULL,
    approver_id text NOT NULL,
    decision text NOT NULL,
    rationale text NOT NULL,
    approved_at timestamptz NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT migration_batch_recovery_approval_id_nonempty
        CHECK (length(btrim(approval_id)) > 0),
    CONSTRAINT migration_batch_recovery_approval_actors_distinct
        CHECK (
            approver_id <> recorded_by
            AND approver_id <> reviewer_id
        ),
    CONSTRAINT migration_batch_recovery_approval_decision_allowed
        CHECK (decision IN ('approved', 'rejected')),
    CONSTRAINT migration_batch_recovery_approval_rationale_nonempty
        CHECK (length(btrim(rationale)) > 0),
    CONSTRAINT migration_batch_recovery_approval_event_unique
        UNIQUE (event_id),
    CONSTRAINT migration_batch_recovery_approval_actor_binding_fk
        FOREIGN KEY (event_id, recorded_by, reviewer_id)
        REFERENCES bravo_shadow.migration_batch_recovery_events
            (event_id, recorded_by, reviewer_id)
        ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS migration_batch_recovery_approvals_history_idx
    ON bravo_shadow.migration_batch_recovery_approvals (event_id, approved_at);

-- Segurança: este rascunho não concede permissões. RLS bloqueia roles comuns
-- até que políticas específicas sejam desenhadas e aprovadas.
ALTER TABLE bravo_shadow.migration_batches ENABLE ROW LEVEL SECURITY;
ALTER TABLE bravo_shadow.migration_source_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE bravo_shadow.migration_batch_recovery_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE bravo_shadow.migration_batch_recovery_approvals ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON SCHEMA bravo_shadow FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL ON TABLE
    bravo_shadow.migration_batches,
    bravo_shadow.migration_source_records,
    bravo_shadow.migration_batch_recovery_events,
    bravo_shadow.migration_batch_recovery_approvals
FROM PUBLIC, anon, authenticated, service_role;

-- NOTAS DE IMPLEMENTAÇÃO OBRIGATÓRIAS:
-- 1. A aplicação valida transições sob lock; CHECK não substitui a máquina de estados.
-- 2. Apply exige status approved, approved_manifest_hash = manifest_hash,
--    ambiente descartável e hash idêntico ao dry-run aprovado.
-- 3. As FKs compostas garantem que vínculos de origem e eventos de recuperação
--    pertençam ao mesmo source_system e manifesto do lote.
-- 4. Em conflito de hash, destino ou identidade, nunca atualizar o vínculo
--    automaticamente. Exigir decisão registrada e novo dry-run.
-- 5. Atualizar last_verified_batch_id somente após verificação completa.
-- 6. Não implementar exclusão automática/rollback por DELETE genérico.
-- 7. Não criar policies/grants usando service_role como atalho.
-- 8. Interrupção em applying/applied sem prova conclusiva deve ir para
--    needs_review, estado terminal. Nunca reabrir ou repetir o mesmo lote.
-- 9. Concorrência de recovery: dentro de uma única transação, primeiro bloquear
--    a linha-pai em migration_batches com SELECT ... FOR UPDATE; validar status
--    needs_review, source_system e manifest_hash; só então calcular
--    COALESCE(MAX(sequence_no), 0) + 1 e inserir o evento. O lock deve ser
--    mantido até COMMIT. A UNIQUE(batch_id, sequence_no) é a última barreira
--    contra duplicidade, não substitui o lock. Se houver conflito, abortar a
--    transação e recarregar o histórico; nunca sobrescrever evento existente.
--    event_id é chave de idempotência global: em repetição, comparar todos os
--    campos do evento existente; aceitar somente se forem idênticos, caso
--    contrário rejeitar como conflito de idempotência. Nunca gerar nova
--    sequência para mascarar uma repetição conflitante.
-- 10. Separação de funções: recorded_by registra; reviewer_id avalia o mérito;
--     approver_id, em tabela separada, aprova ou rejeita. Os três atores devem
--     ser distintos. Só existe uma aprovação final por evento; rejeição encerra
--     aquele evento e qualquer correção exige novo evento de recovery.
--     Para aprovar, bloquear o evento com SELECT ... FOR UPDATE e inserir a
--     aprovação na mesma transação; UNIQUE(event_id) impede dupla aprovação.
--     Aprovação é trilha de auditoria: não altera status, não libera lote e não
--     dispara apply. A imutabilidade efetiva depende de privilégios/trigger na
--     migration futura; este rascunho sozinho não a garante.
-- 11. Recovery exige evento append-only com revisor, justificativa, referência
--     e SHA-256 da evidência. O evento não muda status nem reabre o lote.
--     confirmed_not_committed exige prova da ausência de commit;
--     rollback_verified exige prova da reversão integral;
--     partial_or_unknown mantém o bloqueio.
-- 12. Novo apply sempre exige novo lote/manifesto aprovado. Este arquivo
--     não cria nem altera tabelas funcionais do Bravo.
