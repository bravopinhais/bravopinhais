# Guia de homologação local e gratuita — Bravo Shadow

Data: 27/11/2026

## Decisão de ambiente

A homologação atual está limitada a recursos locais e descartáveis. Não depende de Render, Supabase hospedado, Vercel, Railway, cartão de crédito ou serviço externo.

- Repositório: `bravopinhais/bravopinhais`.
- Branch permitida: `bravo-shadow`.
- PostgreSQL: instância local descartável gerenciada pelo Supabase CLI/Docker.
- Projeto local: `bravo-shadow-local`, definido em `supabase/config.toml`.
- Dados: exclusivamente fixture sintética versionada em `backend/fixtures/migration_homologation_synthetic.json`.
- Produção: nenhuma conexão, segredo, URL, migração ou publicação de produção é permitida.

Não criar projeto remoto nem vincular o CLI a um projeto hospedado. O arquivo local `supabase/.temp/project-ref`, qualquer bloco `[remotes.*]` ou URL remota no ambiente são condições para interromper o procedimento.

## Pré-requisitos locais

- Git.
- Docker instalado e iniciado.
- Supabase CLI instalado.
- Python e dependências do backend instaladas para a avaliação da fixture.
- Checkout atualizado e confirmado na branch `bravo-shadow`.

O procedimento não instala ferramentas automaticamente. Se algum pré-requisito faltar, interrompa e prepare o ambiente antes de prosseguir.

## Etapas

### 1. Confirmar fixture e relatório

A fixture é sintética, pequena e sem dados pessoais. Ela exercita os vínculos legados confirmados entre Financeiro/Plano de Contas e Acertos de Estoque/Estoque. O relatório deve continuar indicando revisão obrigatória para conversões e contratos de domínio ainda não aprovados.

A avaliação integrada é somente leitura e não precisa de banco. A validação automatizada correspondente está em `backend/tests/test_migration_homologation_fixture.py`; os testes ainda não foram executados nesta entrega.

### 2. Conferir isolamento

No diretório `bravo-shadow`, conferir:
- branch exatamente `bravo-shadow`;
- `supabase/config.toml` com `project_id = "bravo-shadow-local"`;
- ausência de vínculo em `supabase/.temp/project-ref` e `.supabase/.temp/project-ref`;
- ausência de remotes no arquivo de configuração;
- ausência das variáveis remotas `SUPABASE_ACCESS_TOKEN`, `SUPABASE_URL`, `SUPABASE_DB_URL`, `SUPABASE_DB_PASSWORD`, `SUPABASE_SERVICE_ROLE_KEY`, `BRAVO_DATABASE_URL` e `BRAVO_SHADOW_TEST_DATABASE_URL`;
- ausência de vínculo CLI em `supabase/.temp/project-ref` e `.supabase/.temp/project-ref`.

O script interrompe a execução se qualquer uma dessas variáveis estiver definida; ele não imprime valores de credenciais. A CLI e o Docker também precisam estar disponíveis localmente.

Se qualquer condição for incerta, não iniciar os serviços.

### 3. Preparar PostgreSQL local descartável

O script `scripts/homologar-local.sh` verifica a branch, a configuração local e o Docker antes de executar `supabase start`, `supabase db reset --local` e `supabase migration list --local`.

**Atenção:** `db reset --local` recria o banco local e remove os dados nele existentes. Executar somente em ambiente descartável, sem dados úteis. O script não usa `--linked`, não cria projeto hospedado e não importa a fixture.

### 4. Homologação de schema e privilégios

Depois que o PostgreSQL local estiver preparado, seguir `plano-homologacao-rls-postgres-descartavel.md`. A inspeção de catálogos somente leitura pode preceder a prova de roles. Criação de roles, memberships, grants, policies e execução de testes destrutivos de integração continuam condicionadas à aprovação específica do desenho e do escopo.

### 5. Ensaio de aplicação

Não faz parte desta etapa. Exige revisão do DDL e adaptador, critérios de domínio aprovados, plano de reversão e aprovação explícita vinculada aos hashes do lote e ao banco descartável. Nenhum dossiê ou relatório de prontidão concede essa autorização.

## Limites e estado

- Nenhum serviço hospedado ou banco remoto deve ser criado.
- Nenhum dado real deve ser usado.
- Nenhuma importação, deploy público, cutover ou alteração na branch de produção está autorizada.
- O script local é destrutivo apenas para o banco local configurado; conferir o alvo antes de executá-lo.
- O estado do ambiente local não foi verificado nesta alteração; nenhum comando Docker/Supabase ou teste foi executado.

A homologação local é gratuita no sentido de não exigir infraestrutura hospedada paga; Docker e ferramentas locais continuam sujeitos aos requisitos e recursos da máquina.
