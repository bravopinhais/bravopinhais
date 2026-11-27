# Fechamento estático de integridade PostgreSQL — Bravo Shadow

**Estado: revisão estática concluída parcialmente; não é homologação PostgreSQL nem autorização de importação.**

## Comparações cobertas

- As 15 coleções do allowlist do adaptador são confrontadas com as tabelas e colunas do DDL funcional.
- Campos obrigatórios Python são comparados com colunas SQL `NOT NULL` sem `DEFAULT`; `id` é injetado pelo adaptador e metadados `created_at`, `updated_at`, `version` permanecem geridos pelo banco.
- Tipos numéricos, `date`, `timestamptz`, nulabilidade e literais de enumeração são comparados com o contrato Python de payload.
- A proveniência é confrontada com a chave primária de identidade de origem, unicidade do destino e nomes de colunas efetivamente usados pelo adaptador.
- A auditoria autenticada é confrontada com as oito colunas do DDL.
- Os campos consultados pelo carregador de autorização, as três tabelas bloqueadas e os estados `approved → applying → applied` são confrontados com os rascunhos SQL.
- As FKs de categoria de documento e motivo de acerto são mantidas como relações de destino sem mapeamento legado confirmado. Não são inferidas a partir de nomes ou textos.

## Integridade referencial conhecida

| Relação | Estado |
|---|---|
| `financeiro.plano_conta_id → plano_contas.id` | FK SQL e referência legada exata conhecida |
| `acertos_estoque.produto_id → estoque.id` | FK SQL e referência legada exata conhecida |
| `documentos.categoria_id → categorias.id` | FK SQL existe; origem legada não confirmada |
| `acertos_estoque.motivo_id → motivos_acerto.id` | FK SQL existe; origem legada não confirmada |

## Bloqueios que permanecem

1. Os SQLs continuam sendo rascunhos; nenhuma comparação textual comprova que o PostgreSQL aceitará a sintaxe ou que o catálogo real corresponda ao texto.
2. O adaptador e os DDLs ainda precisam de uma migration versionada única, sem divergência entre rascunhos evolutivos.
3. As constraints, FKs, índices, RLS, roles, grants, triggers e privilégios efetivos precisam ser inspecionados no PostgreSQL descartável.
4. A transação completa, rollback, colisões concorrentes, bloqueios e resultado de COMMIT incerto precisam de ensaio com dados sintéticos.
5. O contrato de valores rejeita floats para colunas `numeric` e exige timezone explícito em instantes. O produtor do plano de importação deve fornecer valores compatíveis; não há coerção automática.

## Segurança e escopo

Os testes adicionados são estáticos e sintéticos; **não foram executados**. Nenhum SQL foi aplicado, banco conectado, dado importado, role criada, privilégio concedido ou implantação realizada. Não existe autorização para importar dados reais ou executar escrita em produção.
