# Recuperação segura de lotes interrompidos em `applying`

**Status:** protocolo de revisão; não executa recuperação automática.  
**Escopo:** lotes do Bravo Shadow que permanecem em `applying` após interrupção do processo.  
**Ambientes permitidos:** somente `local_disposable` e `ci_ephemeral`.

## 1. Regra de segurança

Um lote encontrado em `applying` nunca deve ser reenviado automaticamente. A interrupção pode ter ocorrido antes da gravação, durante a transação ou depois de o PostgreSQL confirmar o `COMMIT`, mas antes de o processo receber a confirmação/atualizar o estado do lote. Repetir a operação sem determinar o resultado pode duplicar ou conflitar com dados já persistidos.

A recuperação começa em modo somente leitura e termina em decisão humana. Nenhum dado de negócio é corrigido, removido ou regravado por este protocolo.

## 2. Classificação do resultado

| Evidência observada | Classificação | Ação permitida |
|---|---|---|
| Falha anterior ao COMMIT, com rollback confirmado e conexão encerrada | Falha confirmada | Registrar evidência da falha; não reutilizar o lote encerrado |
| COMMIT confirmado e limpeza posterior falhou | Escrita confirmada | Preservar o resultado; auditar separadamente a falha de limpeza |
| Exceção durante COMMIT ou confirmação perdida | Resultado desconhecido | Quarentenar como `needs_review`; nunca repetir automaticamente |
| Lote `applying` sem evidência conclusiva | Resultado desconhecido | Quarentenar como `needs_review`; nunca presumir rollback |

## 3. Procedimento operacional

1. Identificar o lote por `batch_id` e conferir o `manifest_hash`, o ambiente e a aprovação persistida.
2. Não chamar o importador, não recriar o lote e não alterar registros funcionais.
3. Coletar, em transação explicitamente somente leitura, os eventos do lote e o inventário de proveniência associado.
4. Comparar a proveniência com o inventário de origem autorizado, usando a reconciliação existente. Conferir identidade, destino e hash; não consultar payloads desnecessários.
5. Se a execução não puder ser provada como concluída ou revertida, registrar o resultado como desconhecido e mover o lote para `needs_review`, com evento de evidência em transação separada.
6. Encaminhar a divergência para revisão humana. Qualquer nova tentativa exige novo lote, novo dry-run e nova aprovação explícita, após resolução documentada.

## 4. Requisitos transacionais

- As gravações funcionais, o vínculo de proveniência, o evento de sucesso e a auditoria da unidade de escrita devem compartilhar a mesma conexão e transação.
- A falha antes do COMMIT deve produzir rollback integral; a auditoria da falha ocorre somente após o encerramento da conexão original.
- Uma exceção no COMMIT é incerteza, não prova de falha. O callback de resultado desconhecido deve registrar evidência sanitizada e colocar o lote em quarentena sem repetir a escrita.
- Uma falha de limpeza após COMMIT confirmado não pode ser classificada como falha da gravação.
- A mudança para `needs_review` deve usar o adaptador de estado com bloqueio de linha e compare-and-set; conflito concorrente exige nova leitura, nunca atualização forçada.

## 5. Encerramento da revisão

`needs_review` é terminal na máquina de estados atual. Não há transição automática de volta para `approved` ou `applying`. A resolução deve ser documentada fora do fluxo automático. Se uma nova execução for autorizada, ela usa identidade de lote própria e manifesto/dry-run novamente verificados.

## 6. Limites desta etapa

Este documento define o comportamento seguro esperado; não adiciona endpoint, worker, cron, retry, SQL ou migration. Não abre conexão, não consulta o banco, não aplica importação e não valida dados reais. A implementação futura deve ser acompanhada por testes de concorrência e de falha/recuperação em PostgreSQL descartável antes de qualquer uso operacional.
