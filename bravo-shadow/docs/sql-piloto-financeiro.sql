-- RASCUNHO DE SQL — ainda não é uma migration executável.
-- Contém tabelas propostas para Formas Monetárias, Plano de Contas, Financeiro, Estoque e Acertos de Estoque.
-- Copiar para o arquivo criado por "supabase migration new" após revisão.
-- Aplicação prevista somente na stack Supabase LOCAL e isolada do Bravo original.

create schema if not exists bravo_shadow;

-- O schema não será exposto pela Data API.
revoke all on schema bravo_shadow from public;
revoke all on schema bravo_shadow from anon;
revoke all on schema bravo_shadow from authenticated;
revoke all on schema bravo_shadow from service_role;

create table if not exists bravo_shadow.formas_monetarias (
    id text primary key,
    nome text not null,
    -- O legado usa parseFloat sem limites artificiais; double precision preserva
    -- o contrato numérico atual sem impor escala ou faixa não aprovada.
    multa_pct double precision not null default 2.0,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    version bigint not null default 1 check (version >= 1)
);

create index if not exists formas_monetarias_created_at_idx
    on bravo_shadow.formas_monetarias (created_at, id);

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
alter table bravo_shadow.formas_monetarias enable row level security;
alter table bravo_shadow.plano_contas enable row level security;
alter table bravo_shadow.financeiro enable row level security;

-- Cadastro de produtos. Campos mantêm os nomes e formatos do contrato HTTP legado.
create table if not exists bravo_shadow.estoque (
    id text primary key,
    item text not null,
    quantidade integer not null default 1,
    minimo integer not null default 0,
    maximo integer not null default 0,
    etiqueta text not null default '',
    foto_nome text not null default '',
    foto_compactada_gzip text not null default '',
    marca text not null default '',
    linha text not null default '',
    fabricante text not null default '',
    data_cadastro date null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    version bigint not null default 1 check (version >= 1)
);

create index if not exists estoque_item_idx
    on bravo_shadow.estoque (item);

-- Histórico de movimentos. O movimento e o saldo do produto devem ser
-- gravados/atualizados pela mesma transação do backend.
create table if not exists bravo_shadow.acertos_estoque (
    id text primary key,
    data timestamptz not null,
    tipo text not null check (tipo in ('Entrada', 'Saída')),
    produto_id text not null,
    quantidade integer not null check (quantidade > 0),
    motivo text not null,
    motivo_id text null,
    created_at timestamptz not null default now(),
    constraint acertos_estoque_produto_fk
        foreign key (produto_id)
        references bravo_shadow.estoque (id)
        on delete restrict
);

create index if not exists acertos_estoque_produto_data_idx
    on bravo_shadow.acertos_estoque (produto_id, data, id);

create index if not exists acertos_estoque_data_idx
    on bravo_shadow.acertos_estoque (data, id);

alter table bravo_shadow.estoque enable row level security;
alter table bravo_shadow.acertos_estoque enable row level security;

revoke all on table bravo_shadow.formas_monetarias from public, anon, authenticated, service_role;
revoke all on table bravo_shadow.plano_contas from public, anon, authenticated, service_role;
revoke all on table bravo_shadow.financeiro from public, anon, authenticated, service_role;
revoke all on table bravo_shadow.estoque from public, anon, authenticated, service_role;
revoke all on table bravo_shadow.acertos_estoque from public, anon, authenticated, service_role;

-- Não criar GRANT para anon/authenticated/service_role nesta fase.
-- O backend deverá usar um usuário PostgreSQL dedicado, com privilégios mínimos,
-- definido somente depois dos testes locais e da revisão da política de acesso.
