# Auditoria — Dashboard, Relatórios e DRE

## Estado encontrado na branch `bravo-shadow`

- O frontend contém os 15 módulos no menu, mas apenas **Formas Monetárias** está ligado a operações da API nesta tela.
- O Dashboard mostra contagens e textos estáticos de arquitetura. Não consulta a API e não apresenta indicadores financeiros reais.
- Ao abrir **Central de Relatórios & DRE**, o frontend exibe um cartão de módulo ainda não migrado.
- O backend possui `DashboardService` e router `GET /api/v1/dashboard/resumo`, protegido por `dashboard:read`. O endpoint retorna indicadores agregados; a interface ainda não consome esse endpoint.
- Não há router/serviço de Relatórios ou DRE por período/conta. O resumo do Dashboard não equivale a uma DRE completa.
- O domínio Financeiro já existe na API sombra e está conectado ao Plano de Contas pelo serviço de persistência. Isso não significa que a DRE esteja implementada.
- O rascunho de persistência possui tabelas para Financeiro e Plano de Contas, mas nenhuma migration foi aplicada e nenhum banco foi consultado nesta revisão.

## Referência de paridade com o sistema original

A documentação de integridade existente registra o comportamento observado no original:

1. Totais gerais somam todos os títulos, sem filtro por data ou status.
2. A classificação geral usa o tipo do título: `Receber` ou `Pagar`.
3. A DRE agrupa os títulos pela conta de Plano de Contas vinculada.
4. Títulos sem conta vinculada participam dos totais gerais, mas não aparecem em linhas agrupadas por conta.
5. O agrupamento não confere se o tipo do título coincide com o tipo da conta.
6. O indicador chamado “Saldo em Caixa” é apenas Receber menos Pagar; não representa saldo bancário conciliado.

Esses comportamentos são referência histórica, não uma recomendação contábil. Não devem ser alterados silenciosamente durante a migração.

## Limites do contrato atual do Financeiro sombra

O schema atual de `FinanceiroInput` contém:
- `tipo`: Receber ou Pagar;
- `planoContaId`: vínculo opcional;
- `historico`: texto obrigatório;
- `valor`: Decimal com até 14 dígitos e 2 casas decimais.

O contrato não possui data de competência/vencimento, data de pagamento/recebimento, status de liquidação ou conta bancária. Portanto, não permite reproduzir com segurança relatórios por período, fluxo realizado versus previsto, inadimplência ou conciliação bancária. Não inventar esses campos nem derivar status a partir de sinais ou histórico.

## Regras de apresentação segura

- Enquanto não houver endpoint agregado e dados consultados, mostrar “Ainda não calculado” ou “Sem integração”, nunca R$ 0,00 como se fosse um saldo real.
- Distinguir valor total de títulos a receber, valor total de títulos a pagar e diferença aritmética entre os dois.
- Se a diferença aritmética for exibida, nomeá-la explicitamente como “Diferença entre títulos a receber e a pagar”, não “Saldo bancário” ou “Saldo em caixa”.
- Exibir quantidade de registros e data/hora da atualização quando o cálculo estiver conectado.
- Em falha de API, apresentar estado de erro/indisponibilidade; não converter falha em lista vazia nem em total zero.
- Não misturar dados de demonstração com dados reais. Dados fictícios, se futuramente necessários para demonstração visual, devem estar claramente marcados como demonstração.
- Não incluir títulos sem Plano de Contas nas linhas por conta; mantê-los nos totais gerais, em conformidade com a paridade identificada.
- Preservar o vínculo histórico com Plano de Contas. A exclusão de conta referenciada deve continuar bloqueada.

## Arquitetura recomendada para a próxima implementação

1. Manter o serviço agregado de leitura do Dashboard separado dos serviços de cadastro.
2. Usar os serviços de Financeiro e Plano de Contas existentes; evitar carregar ou duplicar registros em outro armazenamento.
3. O endpoint atual `/api/v1/dashboard/resumo` já calcula totais de Receber/Pagar, diferença aritmética e quantidade de títulos com os campos disponíveis.
4. Próxima ampliação possível: agrupamento por conta com código/nome/tipo e totais por tipo de título, mantendo títulos sem conta fora das linhas agrupadas.
5. Não criar filtros por competência, vencimento, liquidação ou período até que o contrato financeiro receba datas e status aprovados.
6. Não chamar a diferença entre Receber e Pagar de saldo bancário. Conciliação exige vínculo de lançamentos com contas bancárias e regras específicas ainda não definidas.
7. Manter autenticação e autorização por capacidade. A matriz de permissões continua sem aprovação; não liberar dados financeiros a perfis reais.
8. Cobrir com testes: lista vazia real, títulos sem conta, contas excluídas/referenciadas, valores Decimal, divergência entre tipo do título e tipo da conta, erro de repositório e consistência dos totais.

## Fora do escopo desta revisão

- Nenhuma alteração no `index.html` original.
- Nenhuma mudança no formulário ou no contrato financeiro.
- Nenhuma migration, conexão com produção ou consulta a dados reais.
- O endpoint agregado do Dashboard já existe e é somente leitura; nenhum endpoint de Relatórios/DRE foi criado nesta etapa.
- Nenhuma matriz de autorização presumida ou ativada.

## Próxima decisão funcional

Antes de construir relatórios por período, confirmar quais datas e estados existem no processo real do Bravo: lançamento, vencimento, competência, pagamento/recebimento e cancelamento. A migração deve preservar os campos originais e não inferir essas informações.


## Implementação incremental — DRE gerencial somente leitura (2026-11-27)

Foi adicionada na branch `bravo-shadow` a rota `GET /api/v1/relatorios/dre`, protegida por `relatorios:read`. O serviço usa diretamente as instâncias existentes de Financeiro e Plano de Contas; não cria repositórios, não grava dados e não altera o contrato dos títulos.

O payload inclui totais e quantidades de Receber/Pagar, diferença aritmética, linhas agrupadas por conta (código, nome, tipo cadastrado, quantidade, valor e participação), quantidade/valor sem conta e instante de atualização. Os cálculos monetários permanecem em Decimal no backend. A classificação do grupo segue o tipo do título, não o tipo da conta, para preservar a regra histórica; o tipo da conta é exibido para transparência.

Títulos sem vínculo ou com vínculo não resolvido permanecem nos totais gerais e são apresentados em indicadores separados, não em linhas agrupadas. Não são aplicados filtros de data ou status, pois esses campos não existem no contrato financeiro atual. A diferença é denominada diferença entre títulos e não representa caixa ou banco.

A tela Shadow foi conectada ao endpoint por meio do cliente entregue em `bravo:session-ready`. A consulta é somente GET, valida a estrutura recebida, insere texto com `textContent`, cancela requisições ao navegar e limpa os dados ao encerrar a sessão. Filtros por período, competência/caixa, conciliação e exportações continuam desabilitados/fora do escopo.

**Evidência e limite:** arquivos versionados na branch Shadow; nenhuma execução de testes, navegação em browser, conexão a banco ou implantação foi realizada nesta etapa. A integração não foi ativada em produção e não consultou dados reais.
