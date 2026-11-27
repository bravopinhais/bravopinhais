# Contratos Python de execução e aprovação de apply

**Status:** modelos puros e validação fail-closed; não habilitam importação.  
**Branch:** `bravo-shadow`.

## Entregue

- `migration_apply_authorization.py` define modelos imutáveis para execução e aprovação.
- O validador exige ambiente `local_disposable`, execução em estado `approved`, decisão `approved`, igualdade exata de lote/execução/manifesto/plano, timestamp com fuso e solicitante diferente do aprovador.
- `migration_transaction.py` deixa de aceitar o ambiente legado `shadow_local`; o valor canônico é `local_disposable`.
- Testes sintéticos foram adicionados para aprovação válida, separação de atores, ambiente/estado, rejeição, hash divergente, timestamp e identidade de execução.

## Limites deliberados

O validador recebe modelos já carregados; não autentica os subjects nem comprova que os registros vieram do PostgreSQL. Isso só poderá ser afirmado por um adapter futuro que carregue lote, execução e aprovação sob locks na mesma transação.

O núcleo `apply_one_record` ainda **não consulta nem exige** esses registros persistidos, não transporta o ator autenticado para auditoria e não possui allowlist SQL de destinos. Portanto, permanece uma unidade experimental não conectada a rotas/composition root. A alteração do ambiente corrige uma incompatibilidade, mas não torna o apply operacional.

## Próximas barreiras

1. Adapter PostgreSQL que bloqueie lote, execução e aprovação e chame este validador com dados persistidos.
2. Capacidade administrativa específica e derivação de solicitante/aprovador a partir de principals autenticados em operações separadas.
3. Campo de auditoria com subject do executor e request ID confiável, na mesma transação do negócio e proveniência.
4. Allowlist fechada por tabela e revisão do DDL, constraints e política de privilégios.
5. Testes de integração/concorrrência em PostgreSQL descartável, somente após autorização específica.

Nenhum SQL foi executado, banco conectado, endpoint ativado, dado real importado ou ambiente de produção alterado. Testes não foram executados.
