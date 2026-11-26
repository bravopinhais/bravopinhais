# Serviço de revisão de migração — integração segura

**Status:** camada de serviço criada, ainda não montada em rotas. Nenhuma capacidade foi aprovada e nenhum banco foi conectado.

## Responsabilidades

`MigrationReviewService` é a fronteira entre identidade autenticada e o adaptador de persistência:
- exige `migration_review:read` para consulta;
- exige `migration_review:append` para registrar evento;
- valida acesso ao lote por política injetada;
- por padrão, a política de acesso ao lote nega tudo;
- deriva `reviewer_id` exclusivamente de `AuthenticatedPrincipal.subject`;
- gera ID e timestamp no servidor;
- valida justificativa antes de persistir.

## Bloqueio intencional neste momento

As capacidades `migration_review:read` e `migration_review:append` ainda não fazem parte de `CAPABILITIES`. Portanto, `require_capability` nega todas as chamadas, inclusive para Admin. Não adicionar essas capacidades nem concedê-las a perfis sem aprovação explícita da matriz.

Também não existe ACL aprovada por lote. O callback `can_access_batch` é obrigatório para permitir qualquer acesso; se não for fornecido, a política padrão nega.

## Integração pendente

- Não criar rota pública ou incluir router no `main.py`.
- Não expor `PostgresReviewSnapshotInitializer` à aplicação web.
- Injetar apenas `PostgresReviewRuntimeStore` no serviço quando as credenciais e grants runtime existirem.
- Resolver a política real de acesso aos lotes antes de habilitar endpoints.
- Testar Google token, capacidades e acesso ao lote em testes de integração.
- Só depois revisar a matriz de perfis e aprovar formalmente as duas capacidades.

## Estado de segurança

Esta camada não cria uma autorização por si só: ela aplica a política existente e falha fechada. Os testes adicionados cobrem negação padrão, bloqueio por lote e derivação do ator a partir do subject Google. Os testes foram escritos, mas não executados.
