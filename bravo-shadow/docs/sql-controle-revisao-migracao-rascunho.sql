-- Bravo Shadow: controle persistente de revisões de migração.
-- RASCUNHO NÃO EXECUTÁVEL EM PRODUÇÃO. Não aplicado a nenhum banco.
-- Pré-requisito: revisar roles, RLS, schema privado e integração com migration_batches.

CREATE SCHEMA IF NOT EXISTS bravo_shadow;

-- A chave externa do lote é textual (ex.: batch-<sha256>), não UUID.
-- Esta tabela registra a identidade do manifesto que foi revisado.
CREATE TABLE IF NOT EXISTS bravo_shadow.migration_review_batches (
    batch_key text PRIMARY KEY,
    manifest_hash char(64) NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT migration_review_batches_key_nonempty
        CHECK (length(trim(batch_key)) > 0),
    CONSTRAINT migration_review_batches_manifest_hash_format
        CHECK (manifest_hash ~ '^[0-9a-f]{64}$')
);

-- A fila de decisões é uma fotografia vinculada ao lote e manifesto.
CREATE TABLE IF NOT EXISTS bravo_shadow.migration_review_decisions (
    decision_id text PRIMARY KEY,
    batch_key text NOT NULL
        REFERENCES bravo_shadow.migration_review_batches(batch_key)
        ON DELETE RESTRICT,
    manifest_hash char(64) NOT NULL,
    decision_kind text NOT NULL,
    decision_status text NOT NULL,
    requires_human boolean NOT NULL DEFAULT true,
    automatic_action text NOT NULL DEFAULT 'none',
    CONSTRAINT migration_review_decisions_batch_decision_unique
        UNIQUE (batch_key, decision_id),
    CONSTRAINT migration_review_decisions_manifest_hash_format
        CHECK (manifest_hash ~ '^[0-9a-f]{64}$'),
    CONSTRAINT migration_review_decisions_no_automatic_action
        CHECK (automatic_action = 'none')
);

-- Eventos são append-only. A role da aplicação não deve receber UPDATE/DELETE.
CREATE TABLE IF NOT EXISTS bravo_shadow.migration_review_events (
    event_id text PRIMARY KEY,
    batch_key text NOT NULL,
    decision_id text NOT NULL,
    manifest_hash char(64) NOT NULL,
    version integer NOT NULL CHECK (version > 0),
    reviewer_id text NOT NULL CHECK (length(trim(reviewer_id)) > 0),
    choice text NOT NULL CHECK (choice IN (
        'approved_for_manual_resolution',
        'keep_blocked',
        'exclude_from_this_batch',
        'request_more_information'
    )),
    rationale text NOT NULL CHECK (length(trim(rationale)) > 0),
    reviewed_at timestamptz NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT migration_review_events_decision_fk
        FOREIGN KEY (batch_key, decision_id)
        REFERENCES bravo_shadow.migration_review_decisions(batch_key, decision_id)
        ON DELETE RESTRICT,
    CONSTRAINT migration_review_events_version_unique
        UNIQUE (batch_key, decision_id, version),
    CONSTRAINT migration_review_events_manifest_hash_format
        CHECK (manifest_hash ~ '^[0-9a-f]{64}$')
);

CREATE INDEX IF NOT EXISTS migration_review_events_history_idx
    ON bravo_shadow.migration_review_events(batch_key, decision_id, version);

-- RLS é habilitada sem policies permissivas. Isso bloqueia acesso até que
-- roles/policies específicas sejam desenhadas, revisadas e aprovadas.
ALTER TABLE bravo_shadow.migration_review_batches ENABLE ROW LEVEL SECURITY;
ALTER TABLE bravo_shadow.migration_review_decisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE bravo_shadow.migration_review_events ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON SCHEMA bravo_shadow FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL ON TABLE
    bravo_shadow.migration_review_batches,
    bravo_shadow.migration_review_decisions,
    bravo_shadow.migration_review_events
FROM PUBLIC, anon, authenticated, service_role;

-- Não conceder grants neste rascunho.
-- Não desabilitar RLS, não usar BYPASSRLS e não usar service_role como atalho.
