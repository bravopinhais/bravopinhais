-- Bravo Shadow versioned migration.
-- Source draft: sql-execucao-aprovacao-apply-rascunho.sql.
-- Promoted to versioned history for disposable/local review only.
-- No production execution or import authorization is implied.


-- Uma execução por lote + plano: impede replay do mesmo plano após falha,
-- resultado incerto ou encerramento. Novo plano exige novo ciclo de aprovação.
CREATE TABLE IF NOT EXISTS bravo_shadow.migration_executions (
    execution_id text PRIMARY KEY,
    batch_id text NOT NULL,
    manifest_hash text NOT NULL,
    plan_sha256 text NOT NULL,
    environment text NOT NULL,
    requested_by_subject text NOT NULL,
    status text NOT NULL DEFAULT 'prepared',
    created_at timestamptz NOT NULL DEFAULT now(),
    started_at timestamptz NULL,
    finished_at timestamptz NULL,

    CONSTRAINT migration_executions_id_nonempty
        CHECK (length(btrim(execution_id)) > 0),
    CONSTRAINT migration_executions_subject_nonempty
        CHECK (length(btrim(requested_by_subject)) > 0),
    CONSTRAINT migration_executions_manifest_hash_format
        CHECK (manifest_hash ~ '^[0-9a-f]{64}$'),
    CONSTRAINT migration_executions_plan_hash_format
        CHECK (plan_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT migration_executions_environment_local_only
        CHECK (environment = 'local_disposable'),
    CONSTRAINT migration_executions_status_allowed
        CHECK (status IN (
            'prepared', 'approved', 'applying', 'applied',
            'failed', 'needs_review'
        )),
    CONSTRAINT migration_executions_time_order
        CHECK (
            (started_at IS NULL OR started_at >= created_at)
            AND (finished_at IS NULL OR finished_at >= created_at)
        ),
    CONSTRAINT migration_executions_batch_manifest_fk
        FOREIGN KEY (batch_id, manifest_hash)
        REFERENCES bravo_shadow.migration_batches(batch_id, manifest_hash)
        ON DELETE RESTRICT,
    CONSTRAINT migration_executions_batch_plan_unique
        UNIQUE (batch_id, plan_sha256),
    CONSTRAINT migration_executions_full_identity_unique
        UNIQUE (execution_id, batch_id, manifest_hash, plan_sha256)
);

CREATE INDEX IF NOT EXISTS migration_executions_batch_status_idx
    ON bravo_shadow.migration_executions (batch_id, status, created_at DESC);

-- Uma única decisão final por execução. Rejeição não pode ser sobrescrita;
-- alteração do plano exige nova execução, com novo hash e nova aprovação.
CREATE TABLE IF NOT EXISTS bravo_shadow.migration_apply_approvals (
    approval_id text PRIMARY KEY,
    execution_id text NOT NULL,
    batch_id text NOT NULL,
    manifest_hash text NOT NULL,
    plan_sha256 text NOT NULL,
    decision text NOT NULL,
    reviewer_subject text NOT NULL,
    rationale text NOT NULL,
    approved_at timestamptz NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT migration_apply_approvals_id_nonempty
        CHECK (length(btrim(approval_id)) > 0),
    CONSTRAINT migration_apply_approvals_reviewer_nonempty
        CHECK (length(btrim(reviewer_subject)) > 0),
    CONSTRAINT migration_apply_approvals_rationale_nonempty
        CHECK (length(btrim(rationale)) > 0),
    CONSTRAINT migration_apply_approvals_decision_allowed
        CHECK (decision IN ('approved', 'rejected')),
    CONSTRAINT migration_apply_approvals_execution_fk
        FOREIGN KEY (execution_id, batch_id, manifest_hash, plan_sha256)
        REFERENCES bravo_shadow.migration_executions
            (execution_id, batch_id, manifest_hash, plan_sha256)
        ON DELETE RESTRICT,
    CONSTRAINT migration_apply_approvals_one_decision_per_execution
        UNIQUE (execution_id)
);

CREATE INDEX IF NOT EXISTS migration_apply_approvals_batch_idx
    ON bravo_shadow.migration_apply_approvals (batch_id, approved_at DESC);

-- RLS bloqueia acesso até que roles/policies dedicadas sejam revisadas.
ALTER TABLE bravo_shadow.migration_executions ENABLE ROW LEVEL SECURITY;
ALTER TABLE bravo_shadow.migration_apply_approvals ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE
    bravo_shadow.migration_executions,
    bravo_shadow.migration_apply_approvals
FROM PUBLIC, anon, authenticated, service_role;

-- REGRAS DE SERVIÇO OBRIGATÓRIAS (não garantidas apenas por este DDL):
-- 1. Ao criar execução, requested_by_subject vem do AuthenticatedPrincipal.subject,
--    nunca do payload; environment é lido do lote e deve ser local_disposable.
-- 2. A criação exige lote/manifesto/plano previamente calculados e imutáveis.
-- 3. O aprovador deve ser um principal autenticado diferente do solicitante.
--    Essa comparação é feita pelo serviço sob lock da execução.
-- 4. Aprovação dry_run_only e migration_batches.approved_* não autorizam apply.
-- 5. O apply bloqueia lote, execução e aprovação, valida todos os hashes e
--    exige decision='approved' antes de tocar em qualquer tabela funcional.
-- 6. O evento de sucesso usa actor_subject do principal executor validado e é
--    inserido na mesma transação que negócio e proveniência.
-- 7. Estados são transicionados sob SELECT ... FOR UPDATE; CHECK não substitui
--    a máquina de estados Python.
-- 8. Execução em failed/needs_review/applied é terminal. Não criar nova
--    execução para repetir o mesmo batch_id + plan_sha256.
-- 9. O DDL não impede UPDATE/DELETE por owner; imutabilidade efetiva depende
--    de role runtime sem esses privilégios e, se necessário, trigger revisado.
-- 10. Não usar service_role, superuser ou BYPASSRLS como atalho.
-- 11. Nenhum registro de negócio deve ser gravado se auditoria ou proveniência
--     falhar; qualquer falha anterior ao COMMIT reverte toda a unidade.
