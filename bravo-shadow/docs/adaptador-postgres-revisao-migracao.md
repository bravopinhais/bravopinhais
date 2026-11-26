# Adaptador PostgreSQL do histórico de revisão — Shadow

**Status:** implementação de código concluída para revisão; não conectada a banco.
O SQL correspondente continua sendo rascunho e não foi aplicado.

## Arquivo

`backend/app/core/migration_review_postgres.py`

A classe `PostgresReviewLedgerStore` implementa o contrato de persistência do
histórico de revisão usando uma fábrica de conexão DB-API injetada. Importar o
módulo não abre conexão nem lê variáveis de ambiente.

## Operações

- `initialize(register)`: cria a identidade do lote e a fotografia da fila
  de decisões uma única vez; em chamadas repetidas, verifica que o manifesto
  e toda a fotografia persistida continuam idênticos. Não substitui registros.
- `load(register)`: apenas lê. Falha se o lote não tiver sido inicializado,
  se o hash divergir, se a fila tiver sido alterada ou se o histórico não
  passar pela verificação de integridade.
- `append(...)`: bloqueia a linha da decisão com `FOR UPDATE`, confere lote,
  manifesto e fotografia, compara `MAX(version)` com `expected_version`,
  valida o evento e insere a nova versão na mesma unidade de trabalho.

O adaptador não atualiza nem apaga eventos. A restrição única no banco continua
sendo a defesa final contra IDs e versões duplicados. Conflitos de integridade
do driver/banco são propagados e provocam rollback pela unidade de trabalho.

## Testes adicionados

`backend/tests/test_migration_review_postgres.py` usa uma conexão simulada
para cobrir inicialização explícita, leitura, histórico append-only, versão
obsoleta, tentativa de reatribuir manifesto e alteração da fotografia de
decisões. A simulação verifica o contrato SQL no nível do adaptador; não
substitui testes de integração com PostgreSQL real.

## Bloqueios mantidos

- Nenhum banco foi conectado.
- Nenhuma migration SQL foi executada.
- RLS continua sem policies e sem grants para o backend.
- Nenhum dado real foi exportado, importado ou alterado.
- A execução dos testes automatizados ainda precisa ocorrer em ambiente Python
  configurado com as dependências do projeto.
- Antes de habilitar o adaptador, revisar schema/roles, RLS, grants mínimos,
  identidade do revisor e isolamento entre lotes em PostgreSQL local.

A implementação é Shadow-only e não altera o `index.html` original.
