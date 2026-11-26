# Supabase local — Bravo Shadow

Este diretório documenta a preparação do banco isolado. Nenhum projeto remoto deve ser vinculado nesta fase.

## Estado atual

- Não há `config.toml` ou `config.jsonc` versionado ainda.
- O DDL de referência está em `../docs/sql-piloto-financeiro.sql`; ele é um rascunho, não uma migration.
- Nenhum banco foi iniciado ou alterado.
- Não existe seed com dados do condomínio.
- Não instalar nem configurar credenciais de produção.
- O backend tem driver Psycopg e fábrica por `BRAVO_DATABASE_URL`, mas o modo padrão continua `memory`. Não habilitar PostgreSQL antes dos critérios de aceite abaixo.

## Versão e preparação local

Use Supabase CLI **3.4.0 ou superior**. A partir da versão 3.4.0, `supabase init` cria `supabase/config.jsonc` em vez de `config.toml`. A CLI v3 executa comandos de banco na stack local por padrão; não use a opção `--remote`.

Na raiz do repositório, entre no diretório `bravo-shadow/` e confira os comandos disponíveis antes de executar:

```bash
supabase --version
supabase --help
supabase init
```

Revise o arquivo de configuração gerado. Confirme que não há `project_id`, referência remota, URL externa ou segredo de produção. Não execute `supabase link`.

Valide a configuração local com:

```bash
supabase config validate
```

## Criar a migration oficial

A migration deve ser criada pela CLI — não crie manualmente o arquivo timestampado:

```bash
supabase migration new bravo_pilot_financeiro
```

Copie o conteúdo revisado de `../docs/sql-piloto-financeiro.sql` para o arquivo timestampado criado em `supabase/migrations/`. Revise o SQL e o diff antes de iniciar o banco.

## Iniciar e validar somente a stack local

```bash
supabase start
supabase status
supabase db reset
supabase migration list
```

O `db reset` sem `--remote` recria a base local e reaplica as migrations. Confirme no output que os serviços e as portas são locais antes de executar comandos de banco. Não use `--remote`, `--linked` ou URL de banco hospedado.

## Critérios de aceite do primeiro lote

1. A migration aplica desde banco vazio sem erro.
2. As tabelas existem exclusivamente no schema privado `bravo_shadow`.
3. `financeiro.plano_conta_id` referencia `plano_contas.id` com `ON DELETE RESTRICT`.
4. `valor` aceita precisão `numeric(14,2)` e rejeita mais de duas casas.
5. RLS está habilitado e não há policies permissivas nem grants a `anon`/`authenticated`.
6. A API não tem credenciais nem driver configurados para banco remoto.
7. Testes de integração usam somente a instância local descartável.
8. Um usuário PostgreSQL dedicado da API recebe somente os privilégios necessários nas três tabelas do piloto; não usar o superusuário padrão da stack como credencial permanente da API.
9. CRUD de Formas Monetárias, Plano de Contas e Financeiro funciona após reiniciar a API e os dados persistem.

Só depois desses critérios deve ser ativado `BRAVO_STORAGE_BACKEND=postgres` na sombra. Não conceder acesso amplo ao schema nem expor `bravo_shadow` pela Data API.

## Comandos proibidos nesta fase

- `supabase link`
- `supabase db push`
- `supabase db reset --remote`
- Qualquer comando com `--remote`, `--linked` ou URL hospedada.

A promoção para staging/produção exige etapa separada, revisão de segurança, backup, plano de rollback e aprovação explícita.

## Limitação deste ambiente de trabalho

O ambiente remoto usado para editar o repositório não tem Supabase CLI nem Docker disponíveis. Portanto, não é possível gerar a migration com a CLI, iniciar a stack ou validar SQL neste ambiente. Esses comandos precisam ser executados em uma máquina de desenvolvimento com Docker e Supabase CLI instalados. Até lá, o rascunho SQL permanece apenas documentação e o backend deve continuar em memória.
