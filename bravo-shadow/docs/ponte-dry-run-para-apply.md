# Ponte entre dry-run e aplicação transacional

## Estado

O módulo `backend/app/core/migration_apply_command_builder.py` transforma um
`DryRunReport` íntegro em comandos imutáveis para o coordenador de lote.
Ele é uma etapa de preparação, não um executor e não concede autorização.

## Barreiras obrigatórias

1. O manifesto precisa ser o mesmo que originou o dry-run: hash do manifesto e
   hash bruto da origem devem coincidir.
2. O relatório precisa estar concluído, sem rollback simulado, com aprovação de
   dry-run verificada e `writes_authorized = false`.
3. O hash do plano é recalculado a partir das decisões ordenadas, versão do
   algoritmo e metadados de rollback. Divergência interrompe a preparação.
4. Somente decisões `planned_insert` geram comandos. Conflitos, duplicidades,
   registros inválidos e itens já aplicados não geram gravações.
5. O registro original é localizado pela impressão digital da identidade e
   seu hash canônico é calculado novamente. Qualquer alteração desde o dry-run
   bloqueia a preparação.
6. IDs de destino e payloads Bravo devem ser fornecidos explicitamente pelo
   mapeamento revisado. Não há conversão automática do ID legado para o ID
   Bravo, nem inferência de campos de negócio.
7. Os mapas de IDs e payloads precisam conter exatamente as identidades
   classificadas como `planned_insert`; chaves extras ou ausentes bloqueiam.
8. O payload recebe o ID de destino explícito e divergências de ID são
   rejeitadas. A allowlist SQL do adaptador continua sendo uma barreira
   adicional.

## Encadeamento previsto

`envelope imutável -> manifesto -> aprovação humana dry-run -> dry-run -> ponte de comandos -> aprovação persistida de apply -> apply_batch_with_persisted_approval`

A aprovação de dry-run **não** é aprovação de escrita. A aplicação continua
dependendo de lote em ambiente `local_disposable`, modo `apply`, manifesto
explicitamente aprovado, execução/plano correspondentes, revisor distinto do
solicitante e principal Bravo autenticado com conta ativa.

## Uso programático

O chamador deve fornecer `batch_id`, `execution_id`, `destination_ids` e
`target_payloads` após revisão do mapeamento de negócio. Ambos os mapas usam
como chave `identity_fingerprint` do relatório. O retorno é uma tupla de
`MigrationApplyCommand` pronta para validação pelo coordenador.

Este módulo não abre conexão, não consulta banco, não grava, não chama rotas e
não é conectado ao frontend. Não deve receber dados reais até que as pendências
de mapeamento e homologação sejam formalmente resolvidas.
