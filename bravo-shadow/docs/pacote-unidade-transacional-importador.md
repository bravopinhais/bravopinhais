# Pacote de unidade transacional do importador

**Status:** núcleo isolado implementado; adapter SQL, schema, endpoint e execução real não implementados.  
**Branch:** `bravo-shadow`.  
**Escopo:** uma unidade de registro por transação; conexão falsa nos testes; nenhuma conexão PostgreSQL.

## Implementação

`backend/app/core/migration_transaction.py` define:
- comando imutável com identidade opaca da origem, hash/versionamento, destino, payload e hashes do manifesto/plano;
- autorização explícita vinculada ao manifesto e plano, limitada a `shadow_local` e `migration_apply`;
- protocolo estreito de store, recebendo a mesma conexão em todas as operações;
- bloqueio lógico do lote e da identidade antes da leitura do mapa;
- repetição com mesmo hash classificada `already_applied`;
- hash divergente classificado como conflito e ID de destino sem mapa como colisão;
- inserção de negócio, vínculo de proveniência e evento de sucesso antes de um único commit;
- rollback em falhas anteriores ao commit;
- `CommitOutcomeUnknown` quando o commit falha, exigindo reconciliação antes de retry;
- autocommit rejeitado e conexão sempre fechada.

## Limites importantes

O módulo não está ligado a rotas, serviços de negócio ou à configuração de armazenamento. Nenhum adapter SQL foi criado porque o schema definitivo, as constraints, RLS, role de migração e a localização do mapa de proveniência ainda exigem revisão. O adapter futuro deve implementar locks e constraints únicas no banco; o bloqueio em aplicação sozinho não protege contra concorrência.

A autorização tipada é uma barreira local de contrato, não uma autenticação humana nem um substituto para aprovação persistida e validada pelo backend. Não reutilizar a aprovação de pré-importação (`dry_run_only`) para conceder aplicação. Nenhum dado real foi lido ou escrito.

## Testes sintéticos

Os testes cobrem sucesso atômico, falha em cada uma das três gravações, idempotência, hash alterado, colisão, commit incerto, autorização/environment mismatch e autocommit. São doubles em memória e não abrem banco. Conforme orientação, não foram executados.

## Próxima revisão necessária

1. Definir DDL/constraints e role de privilégio mínimo.
2. Implementar adapter SQL com a mesma conexão e locks determinísticos.
3. Definir reconciliação de commit incerto e ledger de falha fora da unidade.
4. Só então avaliar integração isolada e homologação local, mediante autorização específica.
