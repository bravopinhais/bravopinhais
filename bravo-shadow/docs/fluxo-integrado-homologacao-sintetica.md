# Fluxo integrado de homologação sintética

## Orquestração implementada

O módulo `backend/app/core/migration_apply_orchestrator.py` oferece uma
entrada única e explicitamente injetada para o caminho de aplicação:

`manifest + dry-run + snapshot imutável + mapeamento revisado -> comandos -> aprovação persistida -> coordenador transacional`

A função `apply_verified_dry_run` não cria nem presume aprovação de escrita.
Ela delega ao coordenador a leitura bloqueante das linhas persistidas de lote,
execução e aprovação, além da validação do principal ativo.

## Barreiras antes da conexão

O construtor de comandos exige:
- manifesto em estado `awaiting_human_approval`, sem gates pendentes ou falhas de integridade;
- relatório completo, com hash de plano recalculado;
- quantidade de decisões igual à quantidade de registros;
- nenhuma colisão, conflito de hash, duplicidade ou registro inválido;
- somente `planned_insert` como comandos de escrita;
- IDs de destino e payloads completos, explícitos e revisados.

Se não houver comandos de inserção, a orquestração recusa o lote vazio e não
abre conexão.

## Barreiras dentro da transação

O coordenador continua exigindo:
- principal autenticado com conta Bravo ativa;
- ambiente `local_disposable`;
- lote em modo `apply`;
- origem, manifesto e plano correspondentes;
- aprovação persistida do manifesto exato;
- solicitante e revisor distintos;
- bloqueios de identidade, colisão de destino e hashes;
- gravação atômica de destino, proveniência e auditoria.

Falha normal reverte a transação completa. Resultado de COMMIT incerto exige
reconciliação antes de qualquer repetição.

## Limites mantidos

A função não está conectada a rotas, frontend, banco real ou produção. Não
abre conexão por conta própria: recebe uma fábrica descartável injetada.
Nenhum dado real foi carregado. A homologação só poderá ocorrer depois que o
DDL, os contratos de campos e os mapeamentos de destino forem revisados e
aplicados a uma base descartável autorizada.
