-- Bravo Shadow versioned migration.
-- Source draft: sql-controle-revisao-migracao-rascunho.sql.
-- Promoted to versioned history for disposable/local review only.
-- No production execution or import authorization is implied.


CREATE SCHEMA IF NOT EXISTS bravo_shadow;

CREATE TABLE IF NOT EXISTS bravo_shadow.migration_review_batches (
    batch_key text PRIMARY KEY,
    manifest_hash text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT migration_review_batches_key_nonempty
        CHECK (length(trim(batch_key)) > 0),
    CONSTRAINT migration_review_batches_manifest_hash_format
        CHECK (manifest_hash ~ '^[0-9a-f]{64}$'),
    CONSTRAINT migration_review_batches_key_manifest_unique
        UNIQUE (batch_key, manifest_hash)
);

-- decision_id permanece PK global; o gerador deve garantir unicidade global.
-- A chave composta permite que decisões só pertençam ao hash exato do lote.
CREATE TABLE IF NOT EXISTS bravo_shadow.migration_review_decisions (
    decision_id text PRIMARY KEY,
    batch_key text NOT NULL,
    manifest_hash text NOT NULL,
    decision_kind text NOT NULL,
    decision_status text NOT NULL,
    requires_human boolean NOT NULL DEFAULT true,
    automatic_action text NOT NULL DEFAULT 'none',
    CONSTRAINT migration_review_decisions_id_nonempty
        CHECK (length(trim(decision_id)) > 0),
    CONSTRAINT migration_review_decisions_kind_nonempty
        CHECK (length(trim(decision_kind)) > 0),
    CONSTRAINT migration_review_decisions_status_nonempty
        CHECK (length(trim(decision_status)) > 0),
    CONSTRAINT migration_review_decisions_manifest_hash_format
        CHECK (manifest_hash ~ '^[0-9a-f]{64}$'),
    CONSTRAINT migration_review_decisions_no_automatic_action
        CHECK (automatic_action = 'none'),
    CONSTRAINT migration_review_decisions_batch_manifest_fk
        FOREIGN KEY (batch_key, manifest_hash)
        REFERENCES bravo_shadow.migration_review_batches(batch_key, manifest_hash)
        ON DELETE RESTRICT,
    CONSTRAINT migration_review_decisions_batch_decision_manifest_unique
        UNIQUE (batch_key, decision_id, manifest_hash)
);

CREATE TABLE IF NOT EXISTS bravo_shadow.migration_review_events (
    event_id text PRIMARY KEY,
    batch_key text NOT NULL,
    decision_id text NOT NULL,
    manifest_hash text NOT NULL,
    version integer NOT NULL CHECK (version > 0),
    reviewer_id text NOT NULL,
    choice text NOT NULL CHECK (choice IN (
        'approved_for_manual_resolution',
        'keep_blocked',
        'exclude_from_this_batch',
        'request_more_information'
    )),
    rationale text NOT NULL,
    reviewed_at timestamptz NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT migration_review_events_id_nonempty
        CHECK (length(trim(event_id)) > 0),
    CONSTRAINT migration_review_events_reviewer_nonempty
        CHECK (length(trim(reviewer_id)) > 0),
    CONSTRAINT migration_review_events_rationale_nonempty
        CHECK (length(trim(rationale)) > 0),
    CONSTRAINT migration_review_events_manifest_hash_format
        CHECK (manifest_hash ~ '^[0-9a-f]{64}$'),
    CONSTRAINT migration_review_events_decision_manifest_fk
        FOREIGN KEY (batch_key, decision_id, manifest_hash)
        REFERENCES bravo_shadow.migration_review_decisions
            (batch_key, decision_id, manifest_hash)
        ON DELETE RESTRICT,
    CONSTRAINT migration_review_events_version_unique
        UNIQUE (batch_key, decision_id, version)
);

CREATE INDEX IF NOT EXISTS migration_review_events_history_idx
    ON bravo_shadow.migration_review_events(batch_key, decision_id, version);

ALTER TABLE bravo_shadow.migration_review_batches ENABLE ROW LEVEL SECURITY;
ALTER TABLE bravo_shadow.migration_review_decisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE bravo_shadow.migration_review_events ENABLE ROW LEVEL SECURITY;

-- FORCE ROW LEVEL SECURITY deve entrar na migration final junto com policies
-- explícitas para a role de migration e a role privada de runtime.
-- Não ativar FORCE isoladamente: sem policies, até operações administrativas
-- legítimas podem ficar bloqueadas. A role runtime nunca será owner,
-- superuser ou BYPASSRLS.

REVOKE ALL ON SCHEMA bravo_shadow FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL ON TABLE
    bravo_shadow.migration_review_batches,
    bravo_shadow.migration_review_decisions,
    bravo_shadow.migration_review_events
FROM PUBLIC, anon, authenticated, service_role;

-- Sem GRANT neste rascunho: acesso permanece fechado.
-- Não usar service_role como atalho; não executar em produção.
