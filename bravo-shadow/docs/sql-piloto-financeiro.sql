-- RASCUNHO DE SQL — ainda não é uma migration executável.
-- Copiar para o arquivo criado por "supabase migration new" após revisão.
-- Aplicação prevista somente na stack Supabase LOCAL e isolada do Bravo original.

create schema if not exists bravo_shadow;

-- O schema não será exposto pela Data API.
revoke all on schema bravo_shadow from public;
revoke all on schema bravo_shadow from anon;
revoke all on schema bravo_shadow from authenticated;

create table if not exists bravo_shadow.plano_contas (
    id text primary key,
    codigo text not null,
    nome text not null,
    tipo text not null check (tipo in ('Receita', 'Despesa')),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    version bigint not null default 1 check (version >= 1)
);

-- A API trata códigos sem diferenciar maiúsculas/minúsculas; o índice fecha
-- também a condição de corrida entre duas criações/edições concorrentes.
create unique index if not exists plano_contas_codigo_ci_uidx
    on bravo_shadow.plano_contas (lower(codigo));

create table if not exists bravo_shadow.financeiro (
    id text primary key,
    tipo text not null check (tipo in ('Receber', 'Pagar')),
    plano_conta_id text null,
    historico text not null,
    valor numeric(14, 2) not null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    version bigint not null default 1 check (version >= 1),
    constraint financeiro_plano_conta_fk
        foreign key (plano_conta_id)
        references bravo_shadow.plano_contas (id)
        on delete restrict
);

create index if not exists financeiro_plano_conta_id_idx
    on bravo_shadow.financeiro (plano_conta_id);

create index if not exists financeiro_created_at_idx
    on bravo_shadow.financeiro (created_at, id);

-- Defesa em profundidade. Sem policies: clientes da Data API não recebem acesso.
alter table bravo_shadow.plano_contas enable row level security;
alter table bravo_shadow.financeiro enable row level security;

revoke all on table bravo_shadow.plano_contas from public, anon, authenticated;
revoke all on table bravo_shadow.financeiro from public, anon, authenticated;

-- Não criar GRANT para anon/authenticated/service_role nesta fase.
-- O backend deverá usar um usuário PostgreSQL dedicado, com privilégios mínimos,
-- definido somente depois dos testes locais e da revisão da política de acesso.
