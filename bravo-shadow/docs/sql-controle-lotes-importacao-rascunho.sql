-- Bravo Shadow: controle de lotes e proveniência de importação.
-- RASCUNHO DE MODELAGEM — NÃO EXECUTAR / NÃO É MIGRATION.
-- Sem roles, grants, policies, triggers ou conexão configurados neste arquivo.
-- Ambiente permitido na V1: local_disposable e ci_ephemeral.
-- O futuro importador deverá recusar produção; este DDL, isoladamente, não executa essa proteção.

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
            'verified', 'failed', 'rolled_back'
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
        UNIQUE (batch_id, manifest_hash)
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
        FOREIGN KEY (first_batch_id)
        REFERENCES bravo_shadow.migration_batches(batch_id)
        ON DELETE RESTRICT,
    CONSTRAINT migration_source_records_last_batch_fk
        FOREIGN KEY (last_verified_batch_id)
        REFERENCES bravo_shadow.migration_batches(batch_id)
        ON DELETE RESTRICT,
    CONSTRAINT migration_source_records_destination_unique
        UNIQUE (destination_collection, destination_id)
);

CREATE INDEX IF NOT EXISTS migration_source_records_first_batch_idx
    ON bravo_shadow.migration_source_records (first_batch_id);

CREATE INDEX IF NOT EXISTS migration_source_records_last_verified_idx
    ON bravo_shadow.migration_source_records (last_verified_batch_id)
    WHERE last_verified_batch_id IS NOT NULL;

-- Segurança: este rascunho não concede permissões. RLS bloqueia roles comuns
-- até que políticas específicas sejam desenhadas e aprovadas.
ALTER TABLE bravo_shadow.migration_batches ENABLE ROW LEVEL SECURITY;
ALTER TABLE bravo_shadow.migration_source_records ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON SCHEMA bravo_shadow FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL ON TABLE
    bravo_shadow.migration_batches,
    bravo_shadow.migration_source_records
FROM PUBLIC, anon, authenticated, service_role;

-- NOTAS DE IMPLEMENTAÇÃO OBRIGATÓRIAS:
-- 1. A aplicação deve validar a transição de status sob lock; CHECK não
--    substitui a máquina de estados nem a aprovação do manifesto.
-- 2. Apply exige status approved, approved_manifest_hash = manifest_hash,
--    ambiente descartável e hash idêntico ao dry-run aprovado.
-- 3. Inserção do registro funcional e da linha source_records ocorre na
--    mesma transação. Não permitir proveniência parcial.
-- 4. Em conflito de hash, destino ou identidade, nunca executar UPDATE
--    automático do vínculo. Exigir decisão registrada e novo dry-run.
-- 5. Atualizar last_verified_batch_id somente após verificação completa.
-- 6. Não implementar exclusão automática/rollback por DELETE genérico.
-- 7. Não criar policies/grants usando service_role como atalho.
-- 8. Este arquivo não cria nem altera tabelas funcionais do Bravo.
