# Pacote integrado de dry-run — Bravo Shadow

**Status:** planejador lógico read-only implementado; testes sintéticos adicionados e não executados.  
**Branch:** bravo-shadow.  
**Limite:** nenhum banco, arquivo, rede, persistência, importação real, rollback real, deploy ou alteração de main.

## Conteúdo
- Motor puro de planejamento e classificação por registro.
- Hash SHA-256 do registro em JSON UTF-8 com chaves ordenadas e sem normalização de valores.
- Verificação de aprovação específica para dry-run e vínculo ao manifesto.
- Detecção de repetição idempotente, alteração de origem, colisão no destino, ID inválido e identidade duplicada.
- Relatório agregado de divergências e hash determinístico do plano.
- Injeção de falha hipotética para simular rollback sem executar transação.
- Testes sintéticos para os fluxos centrais.

## Classificações
- planned_insert: identidade ainda não mapeada e ID ausente do destino; somente contabilizado.
- already_applied: identidade de origem já vinculada ao mesmo hash.
- conflict_changed_source: identidade vinculada a hash diferente; bloqueia atualização automática.
- destination_id_collision: ID já existe no destino sem vínculo de origem compatível.
- invalid_record: registro inválido, ID ausente ou conteúdo não canonicalizável.
- duplicate_source_identity: identidade repetida no mesmo snapshot.

A identidade combina sistema de origem, coleção e ID legado textual. O relatório expõe fingerprint SHA-256, não o ID nem os valores do registro.

## Hashes e determinismo
O hash bruto do arquivo permanece distinto de snapshotHash. O manifesto exato é vinculado por manifest_sha256. O algoritmo de hash por registro tem versão explícita. O hash do plano é estável para a mesma entrada, mapeamento, manifesto e snapshots do estado anterior.

## Rollback
O parâmetro simulate_failure_after injeta uma falha hipotética depois da quantidade informada de inserções planejadas. O relatório marca simulated_rollback. Nenhuma escrita é feita e nada é revertido em banco. O rollback real dependerá de uma unidade de trabalho PostgreSQL única e de testes em banco local descartável.

## Bloqueios e segurança
Aprovação inválida ou não elegível, manifesto bloqueado, autorização de escrita e mapeamento ambíguo impedem a execução. O módulo não importa adaptadores de armazenamento, não recebe conexão e não gera payloads de destino. Mapeamentos precisam ser explícitos; aliases não são inferidos.

## O que ainda falta antes da importação
1. Confirmar nomes e estruturas de origem com snapshot sintético/anônimo autorizado.
2. Resolver gates de campos, decimais Financeiro, codec de documentos, histórico de estoque e localizador singleton de Condomínio.
3. Implementar mapa de identidade e adaptador transacional real no PostgreSQL local descartável.
4. Validar concorrência, rollback real, commit incerto, RLS e idempotência em integração.
5. Revisar separadamente o relatório e obter autorização explícita antes de qualquer modo de escrita.

**Conclusão:** a camada lógica de dry-run está reunida neste pacote. Isso não significa que a importação esteja liberada; a carga real continua bloqueada pelos gates e pela ausência da camada transacional executável.
