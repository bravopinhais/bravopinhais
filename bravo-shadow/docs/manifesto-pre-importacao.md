# Manifesto de pré-importação

**Branch:** `bravo-shadow`  
**Status:** contrato e construtor determinístico; não é autorização de carga.  
**Escopo:** vincular evidências do snapshot, versões dos contratos e resultado da avaliação antes de qualquer importação.

## Evidências vinculadas

O manifesto contém:
- SHA-256 dos bytes originais e tamanho exato do arquivo;
- `snapshotHash` declarado no envelope, mantido separado do hash bruto;
- versão do envelope, sistema de origem, branch, baseline e data declarada de exportação;
- versões explícitas dos contratos, mapeamentos, importador e schema de destino;
- mapeamentos de coleção explícitos e ordenados;
- status, contadores agregados e códigos do relatório consolidado;
- gates pendentes e estado de prontidão.

O envelope v1 não declara um identificador separado de snapshot. Portanto, nenhum `snapshotId` é inventado: `snapshotHash` é a identidade declarada disponível.

## Canonicalização e hash

A versão `json-sort-keys-utf8-no-whitespace-v1` serializa JSON UTF-8 com chaves ordenadas, sem espaços separadores, sem valores não finitos e sem normalização implícita de conteúdo. O SHA-256 do JSON canônico é o `manifest_sha256`. Mudanças no conteúdo ou nas versões devem produzir outro hash.

O hash bruto do arquivo não é comparado com `snapshotHash`: os dois têm escopos contratuais diferentes.

## Privacidade

O manifesto inclui somente metadados de origem, versões, mapeamentos, contagens e códigos. Não inclui registros, IDs legados, nomes, CPF, documentos, fotos, valores de negócio ou payloads.

## Gate de prontidão

O estado permanece `blocked` se o relatório não for `structurally_clear`, se houver códigos de problema ou gates pendentes. Os gates padrão são:
- confirmação do mapeamento dos campos do snapshot;
- semântica e precisão decimal do Financeiro;
- codec real dos documentos;
- reconciliação do histórico de Estoque;
- localização do objeto singleton de Condomínio.

Mesmo quando todos os gates forem resolvidos e o relatório estiver limpo, o estado máximo produzido é `awaiting_human_approval`. O construtor sempre define `humanApprovalRequired=true` e `writesAuthorized=false`. Aprovação humana, ambiente descartável, dry-run e controles transacionais pertencem a etapas posteriores e independentes.

## Limites

O módulo é puro e determinístico: não lê arquivos, não acessa banco/rede, não persiste, não transforma registros e não dispara importação. A versão do importador registrada é uma declaração externa; não comprova que o importador esteja implementado. Os testes adicionados são sintéticos e não foram executados nesta etapa.
