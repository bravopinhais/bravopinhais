# Contrato SQL do histórico de revisão — Shadow

**Status:** rascunho de schema; não aplicado e não é autorização para conexão.

## Chaves e identidade

O identificador funcional do lote é textual (`batch-<sha256>`). Não o converter
para UUID. A tabela de lotes de revisão guarda `batch_key` e `manifest_hash`;
a decisão e cada evento repetem o hash para permitir verificação de vínculo.

## Tabelas propostas

- `bravo_shadow.migration_review_batches`: identidade do lote/manifesto.
- `bravo_shadow.migration_review_decisions`: fotografia da fila de revisão.
- `bravo_shadow.migration_review_events`: histórico append-only de decisões humanas.

## Concorrência obrigatória no adaptador

Cada inclusão deve executar em uma única transação:

1. Bloquear a linha da decisão (`SELECT ... FOR UPDATE`).
2. Conferir `batch_key` e `manifest_hash` nas tabelas de lote e decisão.
3. Calcular a versão atual com `MAX(version)` para a decisão.
4. Comparar com `expected_version`; divergência encerra com conflito de versão.
5. Inserir o evento com `version = expected_version + 1`.
6. Confirmar a transação.

As restrições únicas de `event_id` e de
`(batch_key, decision_id, version)` são a última defesa contra duplicidade.
A validação prévia na aplicação não substitui essas restrições.

## Imutabilidade

A role de runtime não deve ter UPDATE ou DELETE nos eventos. Correções devem
ser novos eventos. A retenção e eventual arquivamento precisam de política
separada, executada por papel administrativo controlado.

## Segurança ainda bloqueadora

O rascunho habilita RLS e não cria policies nem grants. Portanto, por desenho,
não concede acesso ao backend. Antes de qualquer execução será necessário
definir schema/roles, políticas por operação, vínculo com identidade autenticada,
permissões mínimas e testes locais de isolamento. Não usar `service_role`,
superuser ou `BYPASSRLS` para contornar o bloqueio.

## Limites

- Não cria nem altera tabelas de negócio.
- Não aplica dados de migração.
- Não é migration Supabase pronta para execução.
- Nenhuma conexão local ou hospedada foi aberta.
