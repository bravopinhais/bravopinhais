-- RASCUNHO DE REFERÊNCIA — NÃO É MIGRATION.
-- Não aplicar diretamente. Gerar migration com Supabase CLI quando o ambiente local
-- estiver pronto; revisar nomes de roles, grants, RLS e política de retenção.

CREATE TABLE IF NOT EXISTS bravo_shadow.audit_events (
    event_id text PRIMARY KEY,
    occurred_at timestamptz NOT NULL,
    actor_subject text NOT NULL CHECK (length(btrim(actor_subject)) > 0),
    action text NOT NULL CHECK (length(btrim(action)) > 0),
    entity_type text NOT NULL CHECK (length(btrim(entity_type)) > 0),
    entity_id text NULL CHECK (entity_id IS NULL OR length(btrim(entity_id)) > 0),
    outcome text NOT NULL CHECK (outcome IN ('success', 'denied', 'failure')),
    request_id text NULL CHECK (request_id IS NULL OR length(btrim(request_id)) > 0)
);

CREATE INDEX IF NOT EXISTS audit_events_occurred_at_idx
    ON bravo_shadow.audit_events (occurred_at DESC);

CREATE INDEX IF NOT EXISTS audit_events_actor_time_idx
    ON bravo_shadow.audit_events (actor_subject, occurred_at DESC);

CREATE INDEX IF NOT EXISTS audit_events_action_time_idx
    ON bravo_shadow.audit_events (action, occurred_at DESC);

CREATE INDEX IF NOT EXISTS audit_events_entity_time_idx
    ON bravo_shadow.audit_events (entity_type, entity_id, occurred_at DESC);

-- Defesa em profundidade. Sem policy, RLS bloqueia o acesso por roles comuns.
-- Policies/grants específicos só serão definidos após validar as roles locais.
ALTER TABLE bravo_shadow.audit_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE bravo_shadow.audit_events FORCE ROW LEVEL SECURITY;

-- Não conceder UPDATE ou DELETE à role de execução da API.
-- Definir GRANT INSERT e leitura separada em migration posterior, depois de
-- criar/testar roles dedicadas. Não usar PUBLIC, anon, authenticated ou service_role.
REVOKE ALL ON TABLE bravo_shadow.audit_events FROM PUBLIC;
REVOKE ALL ON TABLE bravo_shadow.audit_events FROM anon;
REVOKE ALL ON TABLE bravo_shadow.audit_events FROM authenticated;
REVOKE ALL ON TABLE bravo_shadow.audit_events FROM service_role;