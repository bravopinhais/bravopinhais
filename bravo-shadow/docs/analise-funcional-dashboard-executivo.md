# Análise funcional — Dashboard Executivo

Data: 2026-11-27  
Escopo: inspeção estática do serviço/rota Shadow e baseline funcional. Nenhum dado real foi consultado.

## Estrutura da tela Shadow criada

- Indicadores executivos: títulos a receber, títulos a pagar, diferença, produtos, moradores e documentos.
- Visão financeira: valores agregados a receber e a pagar, mais referência ao plano de contas e formas monetárias.
- Acesso rápido a Financeiro, Relatórios & DRE, Estoque, Compras x Consumo, Moradores e Documentos.
- Panorama operacional: contas do plano, fornecedores e empregados.
- Central de alertas com explicação explícita dos dados ainda indisponíveis.
- Nota de arquitetura e isolamento do ambiente sombra.

Todos os valores permanecem como indisponíveis. Não há valores de demonstração, gráficos inventados nem alertas deduzidos de contagens.

## Contrato atual da API

Rota: `GET /api/v1/dashboard/resumo`  
Proteção: capacidade `dashboard:read`.

O serviço retorna contagens de:
- formas monetárias;
- contas do plano;
- títulos financeiros;
- produtos de estoque;
- moradores;
- fornecedores;
- empregados;
- documentos.

Também retorna:
- quantidade de títulos `Receber`;
- quantidade de títulos `Pagar`;
- soma dos valores `Receber`;
- soma dos valores `Pagar`;
- diferença entre as duas somas.

O serviço atual consulta cada serviço de listagem e calcula as contagens e totais em memória. Isso é um contrato inicial, não uma solução final de desempenho para bases grandes.

## Recursos de dashboard ainda não disponíveis

O resumo não fornece:
- títulos vencidos e a vencer por faixa de dias;
- inadimplência e aging;
- recebimentos/pagamentos realizados por período;
- fluxo de caixa, saldo bancário consolidado ou conciliação;
- evolução mensal e comparativos com período anterior;
- gráficos de receitas/despesas por conta;
- alertas de estoque mínimo, cobertura e compras excessivas;
- pendências de sincronização, conflitos offline ou saúde de conectividade;
- alertas administrativos, auditoria recente ou atividades recentes;
- filtros por período, unidade, setor ou conta;
- exportação/impressão do painel;
- assistente IA/Gemini e diagnóstico assistido do dashboard.

A baseline do sistema original também inclui recursos transversais como cache offline, nuvem/realtime, fila de pendências, recuperação de conexão, histórico de atividades, backups e relatórios assistidos. A interface atual não os implementa.

## Riscos técnicos do serviço atual

1. O serviço chama `.list()` em oito repositórios e carrega coleções para produzir contagens; documentos podem incluir conteúdo Gzip/Base64. Deve-se migrar para consultas agregadas e projeções de metadados.
2. As leituras ocorrem em chamadas separadas e não necessariamente representam o mesmo instante lógico. Para um dashboard financeiro consistente, usar transação/read snapshot e consultas agregadas coordenadas.
3. O cálculo atual soma todos os títulos por tipo, sem filtro explícito de situação, vencimento, liquidação, cancelamento ou competência. Não chamar esses totais de saldo disponível, caixa realizado ou inadimplência.
4. O indicador `diferenca_titulos` é apenas `valor_receber - valor_pagar`; não representa saldo bancário nem resultado contábil.
5. O frontend não está conectado ao módulo Google e a API HTTPS Shadow não está hospedada. O dashboard deve permanecer bloqueado até ambiente isolado e autenticação validada.

## Plano de evolução

1. Definir indicadores com regras financeiras explícitas e reconciliáveis com o módulo Financeiro e DRE.
2. Criar queries agregadas no PostgreSQL para contagens e somas, excluindo conteúdo binário/documental das consultas.
3. Adotar snapshot/transação consistente e limites de período/filtros.
4. Adicionar endpoints para séries mensais, vencimentos, inadimplência, fluxo de caixa e alertas de estoque com permissões apropriadas.
5. Definir contrato de gráficos, exportação, impressão e responsividade.
6. Integrar assistente IA/diagnóstico somente com controles de privacidade, autorização e evidência de dados.
7. Conectar sessão Google e frontend somente a API HTTPS Shadow independente.
8. Homologar os indicadores com dados sintéticos e reconciliação, sem tocar no banco de produção.

## Situação

- [x] Serviço e rota de resumo atuais inspecionados.
- [x] Tela inicial ampliada com indicadores, visão financeira, atalhos, panorama e central de alertas.
- [x] Limitações e métricas ausentes sinalizadas sem dados fictícios.
- [ ] Agregações eficientes e snapshot consistente.
- [ ] Regras de negócio dos indicadores financeiros definidas.
- [ ] Séries, alertas, gráficos, filtros e exportações.
- [ ] Integração Google/API e homologação.
- [ ] Paridade com os recursos transversais do sistema atual.

**Status: estrutura executiva ampliada; paridade funcional ainda não concluída.** Nenhum teste foi executado nesta etapa.
