-- Vínculo persistente entre conta interna Bravo e identidade Google.
-- Aplicável somente em ambientes descartáveis de homologação nesta fase.
-- Não preenche vínculos existentes, não concede acesso e não altera autenticação.

create table if not exists bravo_shadow.google_identities (
    user_id text primary key,
    issuer text not null
        check (issuer = 'https://accounts.google.com'),
    subject text not null
        check (length(btrim(subject)) > 0),
    verified_email_at_link text not null
        check (length(btrim(verified_email_at_link)) > 0),
    linked_at timestamptz not null default now(),
    linked_by text not null
        check (length(btrim(linked_by)) > 0),
    constraint google_identities_user_fk
        foreign key (user_id)
        references bravo_shadow.usuarios (id)
        on delete restrict,
    constraint google_identities_issuer_subject_uidx
        unique (issuer, subject)
);

create index if not exists google_identities_linked_at_idx
    on bravo_shadow.google_identities (linked_at, user_id);

alter table bravo_shadow.google_identities enable row level security;
alter table bravo_shadow.google_identities force row level security;

revoke all on table bravo_shadow.google_identities
    from public, anon, authenticated, service_role;

-- Sem policies ou grants nesta etapa. A API ainda não consulta esta tabela.
-- O vínculo inicial deverá ocorrer por operação administrativa auditada,
-- em transação única, depois de roles e privilégios mínimos serem homologados.
