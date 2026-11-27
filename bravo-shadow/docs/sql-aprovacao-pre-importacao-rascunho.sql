-- Bravo Shadow: trilha de aprovação documental do manifesto pré-importação.
-- RASCUNHO NÃO EXECUTÁVEL. Não aplicado a nenhum banco.
-- Aprovação limitada a dry-run isolado; nunca autoriza gravação/importação.
-- Autenticação do revisor deve ocorrer no serviço usando identidade interna Bravo.

CREATE SCHEMA IF NOT EXISTS bravo_shadow;

CREATE TABLE IF NOT EXISTS bravo_shadow.pre_import_approval_events (
    event_id text PRIMARY KEY,
    manifest_sha256 text NOT NULL,
    raw_source_sha256 text NOT NULL,
    snapshot_hash text NOT NULL,
    decision text NOT NULL,
    scope text NOT NULL DEFAULT 'dry_run_only',
    writes_authorized boolean NOT NULL DEFAULT false,
    reviewer_id text NOT NULL,
    rationale text NOT NULL,
    sequence_no integer NOT NULL,
    reviewed_at timestamptz NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT pre_import_approval_event_id_nonempty
        CHECK (length(btrim(event_id)) > 0),
    CONSTRAINT pre_import_approval_manifest_hash_format
        CHECK (manifest_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT pre_import_approval_source_hash_format
        CHECK (raw_source_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT pre_import_approval_snapshot_hash_format
        CHECK (snapshot_hash ~ '^[0-9a-f]{64}$'),
    CONSTRAINT pre_import_approval_decision_allowed
        CHECK (decision IN (
            'approved_for_dry_run', 'rejected', 'request_changes'
        )),
    CONSTRAINT pre_import_approval_scope_fixed
        CHECK (scope = 'dry_run_only'),
    CONSTRAINT pre_import_approval_never_authorizes_writes
        CHECK (writes_authorized = false),
    CONSTRAINT pre_import_approval_reviewer_nonempty
        CHECK (length(btrim(reviewer_id)) > 0),
    CONSTRAINT pre_import_approval_rationale_nonempty
        CHECK (length(btrim(rationale)) > 0),
    CONSTRAINT pre_import_approval_sequence_positive
        CHECK (sequence_no > 0),
    CONSTRAINT pre_import_approval_manifest_sequence_unique
        UNIQUE (manifest_sha256, sequence_no)
);

CREATE INDEX IF NOT EXISTS pre_import_approval_history_idx
    ON bravo_shadow.pre_import_approval_events
       (manifest_sha256, sequence_no, reviewed_at);

-- Imutabilidade efetiva: UPDATE/DELETE/TRUNCATE devem ser bloqueados.
-- O dono da função e da tabela deverá ser uma role administrativa separada
-- da role runtime; FORCE RLS, roles, policies e grants serão definidos
-- somente na migration final aprovada.
CREATE OR REPLACE FUNCTION bravo_shadow.reject_pre_import_approval_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'pre_import_approval_events_is_append_only';
END;
$$;

DROP TRIGGER IF EXISTS pre_import_approval_no_update_delete
    ON bravo_shadow.pre_import_approval_events;
CREATE TRIGGER pre_import_approval_no_update_delete
    BEFORE UPDATE OR DELETE ON bravo_shadow.pre_import_approval_events
    FOR EACH ROW EXECUTE FUNCTION bravo_shadow.reject_pre_import_approval_mutation();

DROP TRIGGER IF EXISTS pre_import_approval_no_truncate
    ON bravo_shadow.pre_import_approval_events;
CREATE TRIGGER pre_import_approval_no_truncate
    BEFORE TRUNCATE ON bravo_shadow.pre_import_approval_events
    FOR EACH STATEMENT EXECUTE FUNCTION bravo_shadow.reject_pre_import_approval_mutation();

ALTER TABLE bravo_shadow.pre_import_approval_events ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON SCHEMA bravo_shadow FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL ON TABLE bravo_shadow.pre_import_approval_events
    FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL ON FUNCTION bravo_shadow.reject_pre_import_approval_mutation()
    FROM PUBLIC, anon, authenticated, service_role;

-- Sem GRANT/policies neste rascunho: acesso permanece fechado.
-- A camada de serviço deve, na mesma transação:
-- 1. autenticar o revisor pelo Google e resolver usuário interno Bravo ativo;
-- 2. validar que o manifesto está persistido e seus hashes coincidem;
-- 3. permitir approved_for_dry_run somente com readiness awaiting_human_approval,
--    integridade estrutural limpa e zero gates pendentes;
-- 4. inserir novo evento com sequência monotônica sob lock;
-- 5. tratar event_id repetido como idempotente somente se todos os campos
--    coincidirem; caso contrário, rejeitar conflito;
-- 6. nunca traduzir esta decisão para migration_batches.status='approved'
--    nem para autorização de apply. A aprovação de lote é etapa distinta.
