-- RASCUNHO DE HOMOLOGAÇÃO — NÃO EXECUTAR.
-- Aplicação somente após revisão/aprovação explícita e em banco descartável.
-- A tabela guarda preferências de visibilidade, não permissões.
-- Nenhuma alteração aqui concede capacidades ao usuário.

CREATE TABLE IF NOT EXISTS bravo_shadow.module_settings (
    module_key text PRIMARY KEY,
    enabled boolean NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT module_settings_key_not_empty CHECK (length(trim(module_key)) > 0)
);

ALTER TABLE bravo_shadow.module_settings ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE bravo_shadow.module_settings FROM PUBLIC;
-- Grants e policies deliberadamente ausentes neste rascunho.
