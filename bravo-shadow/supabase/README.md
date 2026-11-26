# Supabase local — Bravo Shadow

Este diretório documenta a preparação do banco isolado. Nenhum projeto remoto deve ser vinculado nesta fase.

## Estado

- Não há `config.toml` ou `config.jsonc` versionado ainda.
- O DDL de referência está em `../docs/sql-piloto-financeiro.sql`; ele é um rascunho, não uma migration.
- Nenhum banco foi iniciado ou alterado.
- Não existe seed com dados do condomínio.
- Não instalar nem configurar credenciais de produção.

## Preparação local (executar na máquina de desenvolvimento)

A partir da raiz `bravo-shadow/`:

```bash
supabase --version
supabase --help
supabase init
```

Revise os arquivos gerados pela versão instalada da CLI e confirme que a configuração não contém referência a projeto remoto. Não execute `supabase link`.

Crie a migration usando o comando da CLI:

```bash
supabase migration new bravo_pilot_financeiro
```

Copie o conteúdo revisado de `../docs/sql-piloto-financeiro.sql` para o arquivo timestampado gerado em `supabase/migrations/`. Revise o SQL antes de prosseguir.

Inicie somente a stack local:

```bash
supabase start
supabase db reset
```

O reset local recria o banco local e reaplica migrations; não use `--linked`. Confirme no output que os serviços são locais antes de executar comandos de banco.

## Critérios de aceite do primeiro lote

1. A migration aplica desde banco vazio sem erro.
2. As tabelas existem exclusivamente no schema privado `bravo_shadow`.
3. `financeiro.plano_conta_id` referencia `plano_contas.id` com `ON DELETE RESTRICT`.
4. `valor` aceita precisão `numeric(14,2)` e rejeita mais de duas casas.
5. RLS está habilitado e não há policies permissivas nem grants a `anon`/`authenticated`.
6. A API não tem credenciais nem driver configurados para banco remoto.
7. Testes de integração usam somente a instância local descartável.

Só depois desses critérios deve ser preparado o usuário PostgreSQL dedicado com privilégios mínimos e a conexão da API. Não conceder acesso amplo ao schema nem expor `bravo_shadow` pela Data API.

## Comandos proibidos nesta fase

- `supabase link`
- `supabase db push`
- `supabase db reset --linked`
- Qualquer comando com `--remote`

A promoção para staging/produção exige etapa separada, revisão de segurança, backup, plano de rollback e aprovação explícita.
