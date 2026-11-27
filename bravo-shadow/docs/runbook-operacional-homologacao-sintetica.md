# Runbook operacional da homologação sintética

## Finalidade

O runbook define a ordem dos controles para um futuro ensaio em ambiente local descartável. Ele é um checklist imutável, não um executor. Não cria conexão, não executa SQL, não gera comandos de aplicação, não altera estados persistidos e não concede autorização.

## Sequência obrigatória

1. **PRE-001 — Integridade:** validar hash e identidade do dossiê.
2. **PRE-002 — Isolamento:** comprovar ausência de rota, segredo e dado de produção.
3. **PRE-003 — Schema:** comparar DDL, adaptador, defaults, NOT NULL, FKs, proveniência e auditoria.
4. **PRE-004 — Dry-run:** reconciliar fixture sintética, inventário, candidatos e plano.
5. **PRE-005 — Revisão:** aprovar conversões, perdas, referências e exceções de domínio.
6. **PRE-006 — Aprovação:** registrar aprovação formal vinculada aos hashes e ao ambiente.
7. **PRE-007 — Aplicação sintética:** somente após os gates anteriores, em banco descartável e com autorização persistida.
8. **PRE-008 — Reconciliação:** conferir contagens, hashes, vínculos e auditoria.
9. **PRE-009 — Descarte:** preservar evidência mínima, revogar credenciais e remover o ambiente.

Nenhum checkpoint pode ser pulado. Cada etapa lista condições de entrada, evidências e situações que exigem interrupção.

## Interrupção e recuperação

- Parar no primeiro bloqueio; não contornar validações.
- Em resultado de COMMIT incerto, não repetir. Reconciliar batch, proveniência e destino primeiro.
- Preservar códigos e hashes sem payloads pessoais.
- Não descartar o ambiente antes de preservar evidências aprovadas.
- Falhas de schema, FK, autorização ou auditoria exigem correção e nova revisão.

## Estado atual

O construtor aceita somente dossiê íntegro no ambiente `shadow-synthetic`, rejeita autorização inesperada e sempre gera `status=blocked`, `executable=false` e `approval_required=true`. A mudança de estado não é implementada aqui.

**Limite:** este pacote não autoriza banco de produção, dados reais, importação real ou cutover. O ensaio de escrita, quando aprovado separadamente, será limitado ao ambiente local descartável.

Testes sintéticos adicionados; não executados.
