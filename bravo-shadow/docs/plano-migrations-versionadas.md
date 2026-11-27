# Bravo Shadow — consolidação de migrations versionadas

## Sequência de referência

| Versão | Arquivo | Origem | Dependência |
|---|---|---|---|
| 001 | `20261127000100_bravo_shadow_core.sql` | `sql-piloto-financeiro.sql` | Cria schema e tabelas funcionais |
| 002 | `20261127000200_bravo_shadow_audit.sql` | `sql-auditoria-rascunho.sql` | Core/schema |
| 003 | `20261127000300_bravo_shadow_migration_batches.sql` | `sql-controle-lotes-importacao-rascunho.sql` | Schema; cria lote e proveniência |
| 004 | `20261127000400_bravo_shadow_migration_execution.sql` | `sql-execucao-aprovacao-apply-rascunho.sql` | Lotes |
| 005 | `20261127000500_bravo_shadow_migration_review.sql` | `sql-controle-revisao-migracao-rascunho.sql` | Schema; revisão documental |
| 006 | `20261127000600_bravo_shadow_pre_import_approval.sql` | `sql-aprovacao-pre-importacao-rascunho.sql` | Schema; aprovação de dry-run |

## Fontes deliberadamente não promovidas

- `sql-configuracoes-modulos-rascunho.sql`: a tabela `module_settings` já está incluída no DDL funcional da versão 001. Reexecutar o fragmento como outra migration criaria histórico duplicado.
- `sql-estoque-compras-consumo-rascunho.sql`: é uma evolução histórica já absorvida pela versão 001, que declara as colunas finais de estoque e as precisões numéricas de três casas. Não executar o `ALTER COLUMN ... USING` antigo: ele poderia converter/arredondar dados de uma instalação anterior sem relatório de perdas.

## Regras de uso

- Os arquivos foram organizados em histórico versionado, sem aplicar SQL.
- A sequência é uma consolidação documental/estática. Ainda não há confirmação por parser PostgreSQL, Supabase CLI, catálogo de banco ou execução local.
- Não rodar `supabase db push`, `supabase migration up`, `psql` ou qualquer aplicação automática neste estágio.
- Antes de homologação: revisar o diff integral, validar nomes e existência de roles do ambiente descartável, inspecionar RLS/policies/grants, triggers, FKs, índices, extensões e transações; depois executar somente em banco descartável recém-criado com dados sintéticos.
- A role de runtime continua sem grants neste pacote. Não usar `service_role`, superuser ou BYPASSRLS como substituto de role mínima.
- O schema `bravo_shadow` permanece fora da exposição pública da Data API.
- Qualquer mudança de SQL após homologação exige nova migration versionada; não editar silenciosamente migrations já aplicadas.

## Limites conhecidos

1. Os SQLs de origem tinham comentários indicando rascunho; os cabeçalhos das cópias versionadas identificam sua origem e não afirmam que foram validados.
2. As regras de negócio que exigem serviço — transições de estado, aprovação, separação de funções, proteção contra replay, auditoria e proveniência na mesma transação — não são garantidas somente pelo DDL.
3. O fluxo de recovery não autoriza reaplicar lote nem desfazer gravações automaticamente.
4. A aprovação pré-importação autoriza apenas dry-run documental; nunca apply.
5. Não há criação de roles/policies/grants de runtime neste conjunto.
6. Nenhum dado real ou sintético foi importado; nenhuma conexão ou implantação foi realizada.
