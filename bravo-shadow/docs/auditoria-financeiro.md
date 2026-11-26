# Auditoria do módulo Financeiro — Bravo Shadow

## Escopo e fonte
Inspeção estática do `index.html` da branch `upgrade/project-hardening`, blob `873dbf37bbcf2082faa0444ac28cb9ca9f8ff21c`. O arquivo original foi apenas lido; nenhuma alteração foi feita nele.

Funções e pontos examinados: `renderFinanceiroView`, `renderModalNovoTitulo`, `salvarModalFinanceiro`, `excluirRegistro`, `renderDashboardView`, `gerarRelatorioInteligenteIA` e `renderRelatoriosCentralView`.

## Contrato de dados efetivamente observado

A coleção é `db.financeiro`, um array de objetos. O formulário de título constrói exatamente estes campos:

| Campo | Origem / regra observada |
|---|---|
| `id` | Edição preserva o ID; novo registro recebe `fin_` + `Date.now()`. |
| `tipo` | Select com `Receber` ou `Pagar`; padrão `Receber`. |
| `planoContaId` | ID selecionado em `db.plano_contas`; pode ficar vazio. |
| `historico` | Texto obrigatório no HTML do formulário; sem outra validação explícita. |
| `valor` | Número decimal, `step=0.01`, convertido por `parseFloat`; valor inválido/vazio vira 0 no código. |

### Regras de gravação
- Cadastro e edição usam a mesma rotina.
- A rotina monta um objeto novo com os cinco campos acima e substitui o objeto existente pelo ID, ou adiciona ao array.
- Ao editar, propriedades extras preexistentes não são preservadas: a gravação reconstrói o objeto apenas com esses campos.
- Após gravar, chama `salvarDados(db)`, fecha o modal e redesenha a tela.
- Não há validação de valor positivo, limite de casas decimais além do controle HTML, unicidade do histórico ou verificação de compatibilidade entre o tipo do título e o tipo da conta selecionada.
- Não há filtro, paginação, status, data de vencimento, data de competência, data de pagamento, baixa, recorrência, parcelamento, juros, multa aplicada, fornecedor/morador, conta bancária, forma monetária, comprovante ou anexo no formulário financeiro observado.
- A exclusão é feita pelo helper genérico `excluirRegistro`: confirmação, filtro do array por ID, salvamento e renderização. Não há proteção específica contra exclusão de lançamentos.

## Dependências e vínculos
- `planoContaId` aponta para `db.plano_contas[].id`; o vínculo é opcional no formulário.
- A listagem resolve o vínculo pelo ID e mostra código/nome; quando não encontra, mostra “Não vinculada”.
- O módulo não lê `formas_monetarias` nem `contas_bancarias` na implementação do formulário financeiro atual.
- Não foi observada relação direta com fornecedores, moradores, empregados ou documentos no fluxo de cadastro de títulos.

## Efeitos no Dashboard e na DRE
- Dashboard e relatório executivo percorrem todos os itens de `db.financeiro`, convertem `valor` com `parseFloat(...) || 0` e somam por `tipo`: `Receber` soma em receitas; `Pagar` soma em despesas.
- O “saldo” apresentado é simplesmente total de Receber menos total de Pagar.
- A DRE também calcula o total geral pela mesma regra e agrupa os valores por `planoContaId` existente.
- A DRE soma o valor em cada conta vinculada sem validar se `f.tipo` corresponde ao tipo da conta do plano.
- Títulos sem conta vinculada entram nos totais gerais da DRE, mas não aparecem em nenhuma linha por conta.
- Não há filtro de data, competência, vencimento, pagamento ou status. Portanto, a tela não representa fluxo de caixa realizado nem um exercício selecionado; é uma soma simples de todos os títulos presentes.
- A nomenclatura “Saldo em Caixa” no Dashboard não corresponde a saldo bancário conciliado: é a diferença entre títulos Receber e Pagar, sem consultar contas bancárias ou situação de liquidação.

## Decisões para a implementação sombra
1. Implementar primeiro paridade estrita com o contrato atual de cinco campos, sem introduzir campos ou regras obrigatórias não existentes.
2. Preservar vínculo opcional com Plano de Contas e os tipos literais `Receber` / `Pagar`.
3. Manter a semântica atual dos totais até que o usuário aprove uma evolução funcional separada.
4. Na API e persistência futura, não aceitar silenciosamente valores inválidos; documentar e testar a compatibilidade necessária com registros históricos antes de endurecer validações.
5. Ligar o verificador de exclusão do Plano de Contas à consulta real por `planoContaId`. Até isso existir, a exclusão permanece bloqueada por segurança.
6. Antes de ampliar o domínio, decidir explicitamente se o Bravo passará a controlar vencimentos, liquidações, parcelas, anexos e conciliação bancária. Esses recursos não foram encontrados no formulário atual e não devem ser presumidos como existentes.

## Limitações da auditoria
Esta é uma inspeção estática do HTML/JavaScript versionado. Não foram executados fluxos na aplicação, nem consultados dados reais do Supabase. A estrutura de dados em produção pode conter propriedades históricas que o formulário atual não exibe; a rotina de edição observada, porém, reconstrói o objeto e descarta propriedades extras ao salvar.

## Implementação inicial na sombra

Após a auditoria, foi criado o primeiro CRUD de homologação em memória:
- `GET /api/v1/financeiro`
- `POST /api/v1/financeiro`
- `PUT /api/v1/financeiro/{id}`
- `DELETE /api/v1/financeiro/{id}`

Schemas e serviço preservam os cinco campos observados. O serviço expõe a consulta `has_plan_account_reference`, ligada ao serviço de Plano de Contas na inicialização da API. Assim, a exclusão de conta no ambiente sombra pode retornar 409 quando houver título vinculado.

**Limite:** os dados permanecem em memória e são perdidos ao reiniciar a API. Não há persistência, autenticação, conexão Supabase nem integração com o frontend. Os testes foram adicionados, mas ainda não executados.
