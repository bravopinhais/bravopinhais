-- RASCUNHO DE EVOLUÇÃO DO CONTRATO DE ESTOQUE — NÃO EXECUTAR.
-- Destino previsto: somente schema bravo_shadow em banco descartável local/CI.
-- Não aplicar em produção nem executar até revisão e aprovação explícitas.
-- Pressupõe que a estrutura inicial de bravo_shadow.estoque e
-- bravo_shadow.acertos_estoque foi criada pelo sql-piloto-financeiro.sql.
--
-- Compatibilidade observada no legado: setor/local, unidade, valor unitário,
-- status ativo/inativo, referência fotoPath e quantidades fracionárias (3 casas).
-- senhaCadeado foi deliberadamente omitido até decisão de segurança.

begin;

alter table bravo_shadow.estoque
    add column if not exists setor text not null default 'Geral / Não definido',
    add column if not exists unidade text not null default 'un',
    add column if not exists valor_unitario numeric(14, 2) not null default 0
        check (valor_unitario >= 0),
    add column if not exists status text not null default 'Ativo'
        check (status in ('Ativo', 'Inativo')),
    add column if not exists cor text not null default '',
    add column if not exists foto_path text not null default '';

alter table bravo_shadow.estoque
    alter column quantidade type numeric(14, 3)
        using quantidade::numeric(14, 3),
    alter column minimo type numeric(14, 3)
        using minimo::numeric(14, 3),
    alter column maximo type numeric(14, 3)
        using maximo::numeric(14, 3);

alter table bravo_shadow.acertos_estoque
    alter column quantidade type numeric(14, 3)
        using quantidade::numeric(14, 3);

create index if not exists estoque_setor_status_idx
    on bravo_shadow.estoque (setor, status, item, id);

create index if not exists estoque_status_item_idx
    on bravo_shadow.estoque (status, item, id);

commit;

-- Não há GRANT, policy RLS, publicação ou mudança de exposição neste rascunho.
-- A senha de cadeado não é armazenada até análise específica.
