# Supabase local — Bravo Shadow

Este diretório contém a configuração local e seis migrations versionadas do Bravo Shadow. O projeto está configurado para uso local e não possui vínculo remoto declarado.

## Estado confirmado no repositório

- Configuração: `config.toml`, com `project_id = "bravo-shadow-local"`.
- Migrations: seis arquivos versionados em `supabase/migrations/`, cobrindo schema funcional, auditoria, lotes, execução/aprovação, revisão e aprovação pré-importação.
- Script operacional: `scripts/homologar-local.sh`, que exige branch `bravo-shadow`, configuração local exata, ausência de vínculo/variáveis remotas, Docker ativo e Supabase CLI. Executa `supabase start`, `supabase db reset --local` e `supabase migration list --local`.
- Driver PostgreSQL: Psycopg 3 está nas dependências do backend.
- Nenhuma aplicação das migrations em banco real foi comprovada nesta revisão.
- Nenhuma importação de dados reais está autorizada.

## Como executar a homologação local

Na raiz do repositório:

```bash
cd bravo-shadow
supabase --version
docker info
bash scripts/homologar-local.sh
```

O script encerra com erro se a branch, configuração ou ambiente não corresponderem às condições locais. Ele não instala ferramentas e não tenta corrigir ou remover vínculos remotos automaticamente.

Depois da execução, conferir o histórico local:

```bash
supabase migration list --local
```

A execução do script deve ocorrer somente em máquina de desenvolvimento com Docker e Supabase CLI instalados. Não executar em diretório com dados úteis ou em ambiente compartilhado.

## Bloqueio de segurança que ainda precisa ser resolvido

As migrations atuais revogam privilégios de `PUBLIC`, `anon`, `authenticated` e `service_role` em objetos sensíveis. Várias tabelas habilitam RLS e permanecem sem policies/grants de runtime. Isso é deliberadamente fechado, mas significa que **a API não pode ser considerada pronta para usar PostgreSQL até existir uma role privada mínima, policies explícitas e grants testados**.

A próxima migration de segurança precisa:
1. Criar/definir uma role de runtime dedicada, sem superuser, sem ownership das tabelas e sem `BYPASSRLS`.
2. Definir policies e grants por tabela e operação, seguindo a matriz de capacidades da API.
3. Manter auditoria e aprovações append-only; a role de runtime não recebe UPDATE/DELETE nessas tabelas.
4. Preservar `acertos_estoque` como histórico imutável conforme o contrato funcional.
5. Testar acesso permitido e negado com a role real de runtime, não com owner ou superuser.
6. Garantir que nenhum segredo, URL ou credencial do Bravo original seja usado.

Não conceder acesso amplo ao schema, não expor `bravo_shadow` pela Data API e não usar `service_role` como atalho.

## Critérios de aceite integrados

1. As seis migrations aplicam desde um PostgreSQL local vazio, na ordem versionada.
2. A auditoria do catálogo é executada **depois** das migrations e confirma tabelas, FKs, índices, CHECKs, tipos, RLS, policies e privilégios.
3. A API inicia com a role privada e executa CRUD persistente para todos os módulos habilitados.
4. Transações de negócio, rollback, concorrência otimista, auditoria e proveniência são verificadas em conjunto.
5. Reiniciar a API não perde registros sintéticos.
6. A suíte inclui cenários de negação de acesso e não depende de privilégios de owner.
7. Todos os testes usam exclusivamente banco descartável local/CI.

## Comandos proibidos

- `supabase link`
- `supabase db push`
- `supabase db reset --remote`
- Qualquer comando com `--remote`, `--linked` ou URL de banco hospedado.

A branch Shadow permanece separada. Homologação local não autoriza publicação, conexão a banco hospedado, importação real nem promoção ao Bravo original.

## Pipeline CI existente e lacuna

O workflow `.github/workflows/bravo-shadow-tests.yml` já constrói o Docker, executa smoke test HTTP e roda a suíte Python com um serviço PostgreSQL descartável. Na versão revisada, o job de PostgreSQL executa uma consulta de catálogo somente leitura, mas **não aplica as seis migrations antes da auditoria**. Portanto, o CI atual não é ainda uma homologação ponta a ponta do schema. A correção prioritária é incluir aplicação das migrations e teste de API no mesmo job integrado, e só então executar a suíte completa.

Consulte `docs/plano-integrado-aceleracao-entrega.md` para a sequência consolidada, os bloqueios e os critérios de conclusão.
