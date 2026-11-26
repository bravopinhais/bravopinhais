# Serviço interno de agregação do Dashboard

O serviço `app.modules.dashboard.service.DashboardService` calcula contagens de cadastros e totais aritméticos dos títulos Financeiros usando os serviços pertencentes à mesma instância da API.

## Indicadores disponíveis internamente

- Contagem de formas monetárias, contas do Plano de Contas, títulos financeiros, produtos, moradores, fornecedores, empregados e documentos.
- Quantidade e soma Decimal dos títulos do tipo `Receber` e `Pagar`.
- Diferença aritmética entre os títulos a receber e a pagar.

## Limites deliberados

- O serviço é interno e **não possui endpoint HTTP nesta etapa**. A matriz de autorização não foi aprovada e as rotas de negócio ainda não estão protegidas integralmente.
- O valor `diferenca_titulos` não é saldo bancário nem saldo conciliado.
- Não há filtros por período, competência, vencimento ou liquidação, pois esses campos não existem no contrato atual de Financeiro.
- Contagem de cadastros não equivale a registros ativos; os contratos atuais não oferecem estado uniforme para todos os módulos.
- O resumo não devolve nomes, documentos, contatos ou históricos pessoais/financeiros.
- As leituras são sequenciais e não representam snapshot transacional consistente durante escrita concorrente. Para um Dashboard financeiro definitivo, implementar consulta agregada transacional no PostgreSQL.
- Valores zerados aqui significam que a coleção consultada está vazia no armazenamento selecionado; não devem ser apresentados como dados reais se a API estiver indisponível ou sem persistência.

## Validação

Foram adicionados testes unitários para coleções vazias, agregação Decimal e ausência de campos pessoais no retorno. Os testes ainda precisam ser executados em ambiente Python.
