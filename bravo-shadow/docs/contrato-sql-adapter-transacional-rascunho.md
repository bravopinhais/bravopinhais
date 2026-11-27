# Contrato SQL do adapter transacional de importação

**Status:** desenho técnico; não executável. **Branch:** `bravo-shadow`.

Este documento define o contrato de locks, unicidade, proveniência e auditoria do futuro adapter de `apply_one_record`. Não é migration. Não executar SQL, abrir conexão, criar objetos de banco, ligar rotas ou importar dados.

## 1. Estruturas que devem ser reutilizadas

- `bravo_shadow.migration_batches`: lote, manifesto, ambiente e estado.
- `bravo_shadow.migration_source_records`: vínculo de identidade de origem para destino.
- `bravo_shadow.audit_events`: auditoria geral.
- `PostgresUnitOfWork`: único proprietário de commit, rollback e fechamento.
- `PostgresSourceRecordStore`: gravação/verificação de proveniência usando a conexão recebida.

Não criar um segundo mapa de proveniência nem atualizar silenciosamente um vínculo existente.

## 2. Lacunas que bloqueiam a implementação

| Tema | Incompatibilidade ou ausência | Decisão necessária |
|---|---|---|
| Ambiente | DDL de lote aceita `local_disposable` e `ci_ephemeral`; núcleo de apply exige `shadow_local` | Unificar enumeração e semântica |
| Execução | `execution_id` existe no comando, mas não há registro persistido correspondente no DDL de lotes | Definir tabela/contrato de execução ligada a lote, manifesto e plano |
| Aprovação | Aprovação pré-importação é `dry_run_only`; não autoriza apply | Definir aprovação humana específica de apply, independente |
| Ator | `audit_events.actor_subject` é obrigatório; comando atual não transporta o principal interno | Incluir ator autenticado validado pelo backend, nunca vindo do payload |
| Destino | `target_collection` é dinâmica | Allowlist fechada e SQL específico por tabela; nunca interpolar identificador externo |
| Hash | DDL usa `source_record_hash`; comando usa `source_record_sha256` | Mapeamento explícito e validação consistente |

Não resolver lacunas com defaults permissivos ou inferências.

## 3. Ordem transacional e locks

Todas as operações usam **a mesma conexão** e uma transação PostgreSQL, com autocommit desligado. Ordem fixa:

1. Bloquear lote e validar manifesto, ambiente, estado e aprovação própria de apply.
2. Bloquear execução e validar `execution_id`, lote, manifesto e hash do plano.
3. Adquirir lock consultivo transacional da identidade de origem.
4. Consultar vínculo de proveniência existente, bloqueando-o se presente.
5. Verificar/inserir o registro de negócio por SQL específico da allowlist.
6. Inserir vínculo de proveniência.
7. Inserir evento de auditoria de sucesso.
8. Um único commit pelo `PostgresUnitOfWork`.

Trecho conceitual de bloqueio do lote:

```sql
SELECT batch_id, manifest_hash, environment, status
FROM bravo_shadow.migration_batches
WHERE batch_id = %s
FOR UPDATE;
```

O adapter deve rejeitar lote ausente, manifesto divergente, ambiente não permitido, estado não elegível ou aprovação específica ausente. Aprovação `dry_run_only` nunca autoriza gravação.

### 3.1 Identidade que ainda não possui linha

`SELECT ... FOR UPDATE` não bloqueia uma linha inexistente. Portanto, serializar a identidade completa com advisory lock transacional, em namespace exclusivo do importador:

```sql
SELECT pg_advisory_xact_lock(
    hashtextextended(
        'bravo-shadow:migration-source:' ||
        %s || ':' || %s || ':' || %s,
        0
    )
);
```

A serialização dos componentes precisa ser inequívoca (canonicalização/escaping definidos antes da implementação). Colisão de hash do advisory lock pode apenas reduzir concorrência; a integridade final permanece nas constraints únicas.

Após o lock:

```sql
SELECT destination_collection, destination_id, source_record_hash
FROM bravo_shadow.migration_source_records
WHERE source_system = %s
  AND source_collection = %s
  AND legacy_id = %s
FOR UPDATE;
```

Regras:
- Sem vínculo: prosseguir para verificação e inserção do destino.
- Mesmo hash e mesmo destino: `already_applied`, sem nova gravação de negócio.
- Hash ou destino diferente: conflito para revisão humana; nunca retarget.
- A PK continua obrigatória mesmo com advisory lock.

## 4. Constraints únicas: autoridade final

Reutilizar as constraints já modeladas em `migration_source_records`:
- PK `(source_system, source_collection, legacy_id)`.
- UNIQUE `(destination_collection, destination_id)`.
- CHECK de hash SHA-256 hexadecimal com 64 caracteres.
- FKs compostas para lote e source_system.

Cada tabela de negócio também deve ter PK/UNIQUE no ID de destino. Consulta prévia não elimina corrida entre verificação e inserção. A constraint do destino é a proteção final.

Em violação de unicidade: não gerar outro ID automaticamente, não sobrescrever, abortar a unidade, classificar colisão para reconciliação e não registrar sucesso.

## 5. Proveniência

O `PostgresSourceRecordStore.record(connection, link)` existente já tenta inserir com `ON CONFLICT DO NOTHING` e, em conflito, compara destino e hash sob `FOR UPDATE`. Reutilizar esse contrato somente se:
- usar a mesma conexão da gravação de negócio;
- lote e identidade estiverem bloqueados;
- divergência for propagada para causar rollback;
- nenhum vínculo anterior for alterado.

Preencher `first_batch_id`. Não atualizar `last_verified_batch_id` durante apply: esse campo só avança após verificação completa do lote.

## 6. Auditoria de sucesso na mesma transação

O evento de sucesso deve ser inserido antes do commit, na mesma conexão:

```sql
INSERT INTO bravo_shadow.audit_events
    (event_id, occurred_at, actor_subject, action,
     entity_type, entity_id, outcome, request_id)
VALUES (%s, %s, %s, %s, %s, %s, 'success', %s);
```

O ator vem do principal interno autenticado e validado pelo backend. O contrato atual precisa transportar essa identidade e um request/correlation ID confiável. Não incluir payload, CPF, e-mail, documento ou valores pessoais da origem.

Falha ao gravar auditoria aborta a unidade inteira: não pode haver negócio confirmado sem proveniência e evento de sucesso.

## 7. Falhas e commit incerto

- Falha antes do commit: rollback da unidade; negócio, proveniência e sucesso de auditoria ausentes.
- Falha do commit: resultado desconhecido; não repetir automaticamente. Reconciliar em operação separada e somente leitura, verificando identidade, destino e evento.
- Falha ao fechar conexão após commit confirmado: classificar como commit confirmado com falha de limpeza; nunca declarar rollback.
- Evento de falha: gravar fora da transação que falhou, em unidade separada e com dados sanitizados.
- Sem evidência conclusiva: manter em revisão; não reabrir nem reaplicar o mesmo lote.

## 8. Testes exigidos antes de integrar

1. Duas sessões concorrentes para a mesma identidade.
2. Duas sessões concorrentes com o mesmo ID de destino.
3. Mesmo hash/destino (idempotência).
4. Mesmo legacy ID com hash alterado.
5. ID de destino existente sem vínculo.
6. Falha após cada uma das três gravações.
7. Commit incerto e reconciliação posterior.
8. Falha de fechamento após commit confirmado.
9. Lote, manifesto, plano ou execução divergentes.
10. RLS e privilégios mínimos da role dedicada.

Testes sintéticos não substituem concorrência real em PostgreSQL. Conforme orientação, não executar testes agora.

## 9. Barreiras mantidas

Nenhum schema, role, grant, policy, trigger ou banco foi alterado. Nenhuma rota chama `apply_one_record`. Nenhuma gravação, dual-write, cutover ou importação ocorreu. Nenhum dado real foi lido ou usado. Produção permanece fora do escopo.

**Próxima etapa segura:** fechar ambiente canônico, persistência da execução, aprovação específica de apply e identidade do ator. Só então desenhar a migration revisada e implementar o adapter atrás da allowlist.
