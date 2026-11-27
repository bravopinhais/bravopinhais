# Adapter PostgreSQL de leitura da autorização de apply

**Status:** implementação isolada, não conectada à aplicação e não executada em banco.

## Comportamento

`migration_apply_authorization_postgres.py` recebe uma conexão já aberta pelo chamador e carrega, nesta ordem fixa, as linhas de lote, execução e aprovação usando `SELECT ... FOR UPDATE`. Em seguida valida ambiente `local_disposable`, estado aprovado, igualdade dos hashes e identidades distintas de solicitante/aprovador por meio do validador puro existente.

O módulo não abre conexão, não comita, não faz rollback e não persiste alterações. O chamador é responsável por manter a mesma transação e os locks até concluir as gravações de negócio, proveniência e auditoria.

## Barreira importante

**Não usar como pré-verificação separada.** Se o chamador confirmar a transação após esta leitura e só depois iniciar o apply, os locks são liberados e surge uma janela TOCTOU. A integração correta exige que este método seja chamado dentro da unidade transacional que fará o apply. O atual `apply_one_record` ainda abre sua própria unidade de trabalho e, portanto, não foi conectado a este adapter.

## Verificações sintéticas preparadas

- Caminho autorizado e ordem de bloqueio.
- Ambiente e estado do lote.
- Aprovação ausente.
- Hash de plano divergente.
- Solicitante igual ao aprovador.
- Ausência de conexão implícita.

Testes não executados. Nenhuma rota, capability, composition root, banco ou importação foi alterada/habilitada.
