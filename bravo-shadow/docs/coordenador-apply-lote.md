# Coordenador transacional de aplicação por lote

Status: implementação no branch `bravo-shadow`; não integrado a rotas, não executado contra banco e não autorizado para dados reais.

## Unidade atômica

A função `apply_batch_with_persisted_approval` recebe uma lista fechada de comandos de registro e executa o lote inteiro em uma única `PostgresUnitOfWork`. A mesma conexão mantém:

1. lock e validação de lote, execução e aprovação persistidos, na ordem definida pelo adaptador de autorização;
2. transição temporária de lote e execução de `approved` para `applying`;
3. lock advisory transacional por identidade de origem;
4. validação de proveniência, hash e colisão de destino;
5. inserção do registro funcional, vínculo de proveniência e auditoria autenticada;
6. transição final de execução e lote para `applied`;
7. um único `COMMIT`.

A transição `applying` não é confirmada isoladamente. Em falha normal, todo o trabalho é revertido e os estados persistidos permanecem `approved`. Isso evita deixar um lote parcialmente aplicado por falha entre registros.

## Barreiras

- Todos os comandos precisam compartilhar lote, execução, sistema de origem, manifesto e plano.
- Identidades de origem e destinos duplicados dentro da própria entrada são rejeitados antes de abrir a transação.
- A autorização persistida é revalidada sob locks; aprovação enviada pelo cliente não é aceita.
- O ator da auditoria vem de `AuthenticatedPrincipal.subject`, com conta `Ativo`.
- Coleções e colunas de destino vêm de allowlist estática; valores usam parâmetros SQL.
- Conflitos de hash, destino ou colisão abortam o lote inteiro.
- O adaptador não abre conexão própria e não executa commit.
- O fluxo de uma única linha continua disponível como primitiva técnica, mas não substitui o coordenador do lote.

## Resultado de commit incerto

Se o driver não confirmar o `COMMIT`, a função lança `CommitOutcomeUnknown`. Não repetir automaticamente. Reconciliar primeiro o estado persistido:

- lote e execução `applied`: confirmar hashes, destinos, proveniência e auditoria;
- lote e execução `approved`: confirmar que não houve aplicação e avaliar nova tentativa conforme o protocolo;
- qualquer divergência ou estado inesperado: bloquear e encaminhar para revisão.

Como todos os registros e estados estão na mesma transação, não se espera um lote parcialmente confirmado.

## Ainda pendente

- Validar os nomes/colunas contra uma migration SQL executável revisada.
- Criar implementação de ambiente PostgreSQL descartável e roles de privilégio mínimo.
- Completar testes sintéticos de rollback, idempotência, colisão, concorrência, aprovação e commit incerto.
- Integrar o importador/orquestrador de dry-run sem expor rota de apply.
- Revisão independente antes de qualquer autorização de execução.

Nenhuma migration foi aplicada, nenhum banco foi conectado e nenhum dado foi importado por esta implementação.
