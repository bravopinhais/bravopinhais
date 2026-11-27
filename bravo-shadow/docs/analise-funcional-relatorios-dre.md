# Análise funcional — Relatórios & DRE

Data: 2026-11-27  
Fonte funcional: implementação `renderRelatoriosCentralView` inspecionada no legado. Escopo estático; sem leitura de dados reais.

## Comportamento legado confirmado

A tela central exibe o Demonstrativo do Resultado (DRE) com:

- seção Receitas Operacionais, listando contas do Plano de Contas com tipo `Receita`;
- seção Despesas Operacionais, listando contas com tipo `Despesa`;
- código e nome de cada conta;
- valor total associado a cada conta;
- Resultado Líquido do Exercício, calculado como receitas totais menos despesas totais;
- identificação visual de Plano de Contas ativo.

O cálculo observado inicializa as contas a partir de `db.plano_contas`, percorre `db.financeiro`, soma os valores de lançamentos do tipo `Receber` no total de receitas e do tipo `Pagar` no total de despesas, e agrega cada valor à conta correspondente por `planoContaId`. A tela não apresenta filtro de datas nesta função.

## Contrato Shadow e lacuna de API

A navegação possui o módulo `relatorios`, mas não foi encontrado diretório/roteador dedicado `backend/app/modules/relatorios` na branch Shadow consultada. Existe capacidade `relatorios:read`, usada pelo relatório Compras x Consumo, mas isso não constitui API da DRE.

A tela inicial Shadow criada nesta etapa contém:
- período inicial e final;
- filtro de Plano de Contas;
- resumo de receitas, despesas e resultado líquido;
- tabelas distintas de receitas e despesas por conta;
- ações previstas para consulta, PDF e Excel, ainda desabilitadas;
- estados vazios explícitos e aviso de que não há dados carregados.

## Decisões contábeis pendentes — não presumir

A regra antiga soma valores dos registros financeiros sem filtrar situação ou data. Antes de criar API com período, é obrigatório definir:
1. DRE por competência ou por caixa.
2. Data de referência: vencimento, lançamento, pagamento ou recebimento.
3. Se títulos em aberto entram no resultado ou apenas valores efetivamente pagos/recebidos.
4. Tratamento de cancelamentos, estornos, baixas parciais, juros, multas e descontos.
5. Inclusão de contas sem movimento, subcontas e lançamentos sem `planoContaId`.
6. Sinal contábil, transferências internas e prevenção de dupla contagem.
7. Como os totais da DRE reconciliam com o módulo Financeiro e com relatórios/exportações.
8. Formatos de PDF/Excel, filtros, ordenação e paginação.

Adicionar filtro de período sem resolver essas regras alteraria silenciosamente o comportamento do relatório e poderia produzir números divergentes. Por isso a interface não calcula totais no navegador e não mostra dados simulados.

## Próximas entregas técnicas

1. Inspecionar os schemas/repositórios de Financeiro e Plano de Contas e mapear campos de data, status, baixas e vínculos.
2. Formalizar a regra contábil com exemplos sintéticos e casos de borda.
3. Criar serviço de domínio de DRE e endpoint protegido por `relatorios:read`, com consultas agregadas no banco e sem carregar todos os títulos para o cliente.
4. Implementar filtros e metadados de período, com totais reconciliáveis.
5. Implementar exportação CSV/Excel e PDF/impressão após estabilizar o contrato.
6. Conectar frontend somente após API HTTPS Shadow independente e sessão Google ativa.
7. Homologar com dados sintéticos, comparando cada conta e total com cálculos de referência.

## Situação

- [x] Função DRE legada inspecionada.
- [x] Regra de soma por tipo e agregação por plano de contas documentada.
- [x] Tela Shadow inicial criada, sem dados simulados.
- [x] Ausência de router DRE dedicado registrada.
- [ ] Regra competência/caixa e situações financeiras formalizadas.
- [ ] Serviço/API DRE implementados.
- [ ] Filtros, PDF/Excel e reconciliação implementados.
- [ ] Integração e homologação funcional.

**Status: estrutura inicial, não paridade concluída.** Nenhum teste foi executado nesta etapa.
