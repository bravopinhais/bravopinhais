-- RASCUNHO DE SQL — ainda não é uma migration executável.
-- Contém tabelas propostas para cadastros financeiros, estoque, catálogos e documentos.
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

-- Cadastros administrativos e dados pessoais: acesso somente pelo backend.
create table if not exists bravo_shadow.moradores (
    id text primary key,
    bloco text not null,
    apartamento text not null,
    nome text not null,
    email text not null default '',
    telefone text not null default '',
    cpf text not null default '',
    pet_nome text not null default '',
    vaga_garagem text not null default '',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    version bigint not null default 1 check (version >= 1)
);

create index if not exists moradores_bloco_apartamento_idx
    on bravo_shadow.moradores (bloco, apartamento, nome, id);

create table if not exists bravo_shadow.fornecedores (
    id text primary key,
    cnpj text not null,
    razao_social text not null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    version bigint not null default 1 check (version >= 1)
);

create index if not exists fornecedores_razao_social_idx
    on bravo_shadow.fornecedores (razao_social, id);

create table if not exists bravo_shadow.empregados (
    id text primary key,
    nome text not null,
    cargo text not null,
    empresa text not null default '',
    endereco text not null default '',
    telefone text not null default '',
    contato_emergencia_nome text not null default '',
    contato_emergencia_tel text not null default '',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    version bigint not null default 1 check (version >= 1)
);

create index if not exists empregados_nome_idx
    on bravo_shadow.empregados (nome, id);

create table if not exists bravo_shadow.contas_bancarias (
    id text primary key,
    banco text not null,
    saldo numeric(14, 2) not null default 0,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    version bigint not null default 1 check (version >= 1)
);

create index if not exists contas_bancarias_banco_idx
    on bravo_shadow.contas_bancarias (banco, id);

-- Dados institucionais do condomínio e membros do conselho.
-- Colunas camelCase são mantidas entre aspas para refletir o contrato legado.
create table if not exists bravo_shadow.condominio (
    id text primary key,
    "nome" text not null default '',
    "cnpj" text not null default '',
    "razaoSocial" text not null default '',
    "endereco" text not null default '',
    "bairro" text not null default '',
    "cidade" text not null default '',
    "uf" text not null default '',
    "cep" text not null default '',
    "telefone" text not null default '',
    "email" text not null default '',
    "copelBloco1" text not null default '',
    "copelBloco2" text not null default '',
    "copelBloco3" text not null default '',
    "copelBloco4" text not null default '',
    "copelAreasComuns" text not null default '',
    "gasSalao" text not null default '',
    "sanepar" text not null default '',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    version bigint not null default 1 check (version >= 1)
);

create table if not exists bravo_shadow.conselheiros (
    id text primary key,
    nome text not null,
    cargo text not null,
    "BlocoAp" text not null default '',
    telefone text not null default '',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    version bigint not null default 1 check (version >= 1)
);

create index if not exists conselheiros_nome_idx
    on bravo_shadow.conselheiros (nome, id);

-- Perfis de aplicação vinculados ao e-mail Google já verificado pelo fluxo de autenticação.
-- Esta tabela não autentica usuários nem concede autorização por perfil.
create table if not exists bravo_shadow.usuarios (
    id text primary key,
    email text not null,
    nome text not null,
    loja text not null default 'Guardiões do Bravo',
    cargo text not null,
    perfil text not null default 'Operador' check (perfil in ('Admin', 'Operador')),
    status text not null default 'Ativo' check (status in ('Ativo', 'Inativo')),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    version bigint not null default 1 check (version >= 1)
);

create unique index if not exists usuarios_email_ci_uidx
    on bravo_shadow.usuarios (lower(btrim(email)));

create index if not exists usuarios_nome_idx
    on bravo_shadow.usuarios (nome, id);

-- Defesa em profundidade. Sem policies: clientes da Data API não recebem acesso.
alter table bravo_shadow.formas_monetarias enable row level security;
alter table bravo_shadow.plano_contas enable row level security;
alter table bravo_shadow.financeiro enable row level security;

-- Cadastro de produtos. Campos mantêm os nomes e formatos do contrato HTTP legado.
create table if not exists bravo_shadow.estoque (
    id text primary key,
    item text not null,
    quantidade numeric(14, 3) not null default 1 check (quantidade >= 0),
    minimo numeric(14, 3) not null default 0 check (minimo >= 0),
    maximo numeric(14, 3) not null default 0 check (maximo >= 0),
    etiqueta text not null default '',
    foto_nome text not null default '',
    foto_compactada_gzip text not null default '',
    marca text not null default '',
    linha text not null default '',
    fabricante text not null default '',
    data_cadastro date null,
    setor text not null default 'Geral / Não definido',
    unidade text not null default 'un',
    valor_unitario numeric(14, 2) not null default 0 check (valor_unitario >= 0),
    status text not null default 'Ativo' check (status in ('Ativo', 'Inativo')),
    cor text not null default '',
    foto_path text not null default '',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    version bigint not null default 1 check (version >= 1)
);

create index if not exists estoque_item_idx
    on bravo_shadow.estoque (item);

create index if not exists estoque_setor_status_idx
    on bravo_shadow.estoque (setor, status, item, id);

-- Catálogos com IDs estáveis para manter os vínculos referenciais.
create table if not exists bravo_shadow.categorias (
    id text primary key,
    nome text not null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    version bigint not null default 1 check (version >= 1)
);

create index if not exists categorias_nome_idx
    on bravo_shadow.categorias (nome, id);

create table if not exists bravo_shadow.motivos_acerto (
    id text primary key,
    nome text not null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    version bigint not null default 1 check (version >= 1)
);

create index if not exists motivos_acerto_nome_idx
    on bravo_shadow.motivos_acerto (nome, id);

-- Mantém o conteúdo compactado legado como texto; não migra arquivos para
-- Supabase Storage nem altera o formato/base64 nesta etapa.
create table if not exists bravo_shadow.documentos (
    id text primary key,
    pasta text not null default 'Geral',
    categoria_id text null,
    titulo text not null,
    nome_arquivo text not null,
    arquivo_compactado_gzip text not null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    version bigint not null default 1 check (version >= 1),
    constraint documentos_categoria_fk
        foreign key (categoria_id)
        references bravo_shadow.categorias (id)
        on delete restrict
);

create index if not exists documentos_categoria_id_idx
    on bravo_shadow.documentos (categoria_id);

create index if not exists documentos_created_at_idx
    on bravo_shadow.documentos (created_at, id);

-- Histórico de movimentos. O movimento e o saldo do produto devem ser
-- gravados/atualizados pela mesma transação do backend.
create table if not exists bravo_shadow.acertos_estoque (
    id text primary key,
    data timestamptz not null,
    tipo text not null check (tipo in ('Entrada', 'Saída')),
    produto_id text not null,
    quantidade numeric(14, 3) not null check (quantidade > 0),
    motivo text not null,
    motivo_id text null,
    created_at timestamptz not null default now(),
    constraint acertos_estoque_produto_fk
        foreign key (produto_id)
        references bravo_shadow.estoque (id)
        on delete restrict,
    constraint acertos_estoque_motivo_fk
        foreign key (motivo_id)
        references bravo_shadow.motivos_acerto (id)
        on delete restrict
);

create index if not exists acertos_estoque_produto_data_idx
    on bravo_shadow.acertos_estoque (produto_id, data, id);

create index if not exists acertos_estoque_data_idx
    on bravo_shadow.acertos_estoque (data, id);

alter table bravo_shadow.estoque enable row level security;
alter table bravo_shadow.acertos_estoque enable row level security;
alter table bravo_shadow.categorias enable row level security;
alter table bravo_shadow.motivos_acerto enable row level security;
alter table bravo_shadow.documentos enable row level security;
alter table bravo_shadow.moradores enable row level security;
alter table bravo_shadow.fornecedores enable row level security;
alter table bravo_shadow.empregados enable row level security;
alter table bravo_shadow.contas_bancarias enable row level security;
alter table bravo_shadow.condominio enable row level security;
alter table bravo_shadow.conselheiros enable row level security;
alter table bravo_shadow.usuarios enable row level security;

revoke all on table bravo_shadow.formas_monetarias from public, anon, authenticated, service_role;
revoke all on table bravo_shadow.plano_contas from public, anon, authenticated, service_role;
revoke all on table bravo_shadow.financeiro from public, anon, authenticated, service_role;
revoke all on table bravo_shadow.estoque from public, anon, authenticated, service_role;
revoke all on table bravo_shadow.acertos_estoque from public, anon, authenticated, service_role;
revoke all on table bravo_shadow.categorias from public, anon, authenticated, service_role;
revoke all on table bravo_shadow.motivos_acerto from public, anon, authenticated, service_role;
revoke all on table bravo_shadow.documentos from public, anon, authenticated, service_role;
revoke all on table bravo_shadow.moradores from public, anon, authenticated, service_role;
revoke all on table bravo_shadow.fornecedores from public, anon, authenticated, service_role;
revoke all on table bravo_shadow.empregados from public, anon, authenticated, service_role;
revoke all on table bravo_shadow.contas_bancarias from public, anon, authenticated, service_role;
revoke all on table bravo_shadow.condominio from public, anon, authenticated, service_role;
revoke all on table bravo_shadow.conselheiros from public, anon, authenticated, service_role;
revoke all on table bravo_shadow.usuarios from public, anon, authenticated, service_role;

-- Não criar GRANT para anon/authenticated/service_role nesta fase.
-- O backend deverá usar um usuário PostgreSQL dedicado, com privilégios mínimos,
-- definido somente depois dos testes locais e da revisão da política de acesso.


-- Política de imutabilidade: o papel dedicado da API não deve receber
-- DELETE em bravo_shadow.acertos_estoque. Correções devem ser lançadas como
-- movimentos compensatórios após implementação do fluxo específico.
-- Não conceder DELETE nessa tabela ao usuário PostgreSQL da aplicação.
