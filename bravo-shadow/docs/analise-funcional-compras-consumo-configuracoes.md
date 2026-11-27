# Análise funcional — Compras x Consumo e Configurações

Data da inspeção: 2026-11-27  
Branch de trabalho: `bravo-shadow`  
Fonte de referência: `index.html` da branch `main` (blob `2f55d89b14ce45e1df643fe4af5a1218704fdb71`). Interface Shadow inspecionada: `bravo-shadow/frontend/index.html` (blob `d06eb5cfc4d9f9d83b666fb73e7e8163ee98a526`).

## Limites desta etapa

Inspeção estática do código-fonte. Não houve login, navegação real em browser, conexão com banco, execução de SQL, migração, testes ou publicação. Esta análise não autoriza reaproveitar dados de produção nem conectar o Shadow ao backend de produção.

## 1. Compras x Consumo — comportamento que precisa ser preservado

### Fonte de dados e relacionamento

O relatório é calculado a partir de:
- `db.acertos_estoque`: movimentos com `produtoId`, `data`, `tipo`, `motivo` e `quantidade`.
- `db.estoque`: cadastro atual do produto, relacionado por `id`, com `item`, `etiqueta`, `marca`, `quantidade`, `minimo`, `maximo`, `valorUnitario` e unidade de medida.
- Setor e unidade são resolvidos pelas funções compartilhadas `setorEstoque`, `obterSetoresEstoque` e `unidadeDoItem`.

Não foi identificado um cadastro independente de compras nesta tela: o relatório interpreta os movimentos de Acerto de Estoque. Uma implementação que invente pedidos, notas fiscais ou lançamentos de compras independentes não seria equivalente.

### Classificação dos movimentos

- Entrada: se o filtro “Tratar todas as entradas como compras” estiver ligado, toda entrada é compra; desligado, só motivos que correspondam a compra/reposição contam como compra e as demais entradas ficam separadas.
- Saída: motivos que correspondam a perda, avaria, quebra, ajuste ou inventário são classificados como perdas/ajustes; demais saídas contam como consumo.
- A classificação considera `tipo` iniciando por “entr” e o texto de `motivo`.

### Filtros e período

- Períodos: mês atual, últimos 30, 90 e 180 dias, ano atual, todo histórico e intervalo personalizado.
- Intervalo personalizado aceita datas inicial/final.
- Setor: Todos ou setor do produto.
- Busca por nome, etiqueta/código e marca.
- Ordenação: maior consumo, maior compra, diferença compras-consumo, menor cobertura ou nome.
- Alternância para tratar todas as entradas como compras.
- Registros sem data válida são ignorados e contabilizados no aviso.

### Cálculos e regras

- Quantidades são agrupadas por produto e mês.
- Valor financeiro usa o valor unitário atual do cadastro do produto multiplicado pelas quantidades históricas. Itens sem valor unitário não entram nas somas valorizadas.
- A série mensal apresenta até 12 meses, em reais quando há valor cadastrado; sem valores, apresenta quantidade apenas se todos os produtos filtrados compartilharem a mesma unidade.
- Indicadores: compras/gasto, consumo, perdas/ajustes e quantidade de produtos em alerta.
- Diferença = compras - consumo.
- Consumo médio mensal = consumo / meses do período.
- Cobertura = estoque atual / consumo médio mensal, quando há estoque atual e consumo positivo.
- Situações: Equilibrado, Produto eliminado, Comprado sem consumo, Sem consumo, Repor, Cobertura baixa e Comprando acima do uso.
- Reposição: estoque atual menor ou igual ao mínimo.
- Cobertura baixa: cobertura menor que um mês.
- Compra excessiva: compras acima de 1,5× consumo, máximo configurado e estoque atual acima do máximo.
- Produtos eliminados permanecem visíveis no relatório quando há movimentos históricos, com identificação explícita.

### Saídas

- Tabela por produto com código, produto/setor, compras, outras entradas (quando aplicável), consumo, perdas/ajustes, diferença, estoque atual, média mensal, cobertura, valores comprados/consumidos quando disponíveis e situação.
- Impressão / PDF pelo diálogo de impressão.
- Exportação CSV compatível com Excel, com unidade, valores unitários e totais, período e situação.
- KPIs, evolução mensal e avisos contextuais.

### Dependências para implementação Shadow

Antes de expor o relatório:
1. Confirmar o contrato de dados e enumerações do módulo Acerto de Estoque Shadow.
2. Garantir que o cadastro de estoque preserve unidade, setor, saldo, mínimo, máximo e valor unitário; incluir também os campos adicionais solicitados para estoque (marca, linha, fabricante e data de cadastro), sem alterar a semântica existente.
3. Implementar serviço de leitura que consuma os repositórios Shadow de estoque e acertos, sem escrever ou recalcular saldos.
4. Manter os cálculos no servidor ou em uma camada de domínio pura com contrato explícito; não aceitar parâmetros que permitam consultar produção.
5. Entregar filtros, tabela, série, KPIs, impressão e CSV antes de considerar o módulo equivalente.

## 2. Configurações — comportamento que precisa ser preservado

### Configuração de disponibilidade dos módulos

A produção define uma lista de módulos configuráveis com identificador, nome, descrição, grupo e ícone. A configuração é armazenada em `db.configuracoes.modulos`; ausências são inicializadas como ativas. Configurações é sempre acessível para permitir reativação.

O administrador pode:
- Ativar ou desativar um módulo individual.
- Ativar todos.
- Desativar os módulos operacionais em conjunto, mantendo Configurações disponível.
- Ao desativar um módulo aberto, o sistema fecha sua aba e retorna a Configurações.
- A operação não exclui registros.

A produção exige perfil/cargo de administrador para entrar em Configurações e alterar os módulos. No Shadow, esta regra deve ser aplicada pela autorização do backend (capacidade administrativa) e não apenas por ocultação de botões ou verificação de texto no frontend.

### Painéis incluídos na tela de Configurações da produção

A tela não é apenas uma lista de módulos. Ela agrega:
- Animações e efeitos visuais: preferência local por dispositivo.
- Assistente Gemini: estado/configuração da IA e orientação sobre chamada remota.
- Proteção, sincronização e atualizações: estado de autenticação/sincronização, guia de segurança, backup JSON e gestão de cópias automáticas.
- Histórico de atividades: eventos recentes derivados de registros do sistema.
- Saúde do sistema: indicadores locais, conexão e sincronização, com ação de diagnóstico.
- Lista de módulos agrupados, estado ativo/inativo e ações em lote.

A produção também contém fluxos transversais separados para backups, recuperação, diagnóstico de nuvem, auditoria e configuração de IA. Não se deve exibir estado “conectado”, “sincronizado”, “backup automático” ou “IA ativa” no Shadow sem uma implementação real correspondente.

### Regras de migração para Shadow

- Preferências visuais não críticas podem ser locais ao dispositivo, com escopo documentado.
- Disponibilidade de módulos e preferências administrativas devem ser persistidas no backend e auditadas.
- A configuração não pode conceder capacidades: desativar/ativar um módulo controla sua disponibilidade funcional, enquanto autorização por perfil/capacidade continua sendo verificada em cada endpoint.
- Operações em lote devem exigir confirmação e registrar ator, alteração anterior/nova e horário.
- Operador não pode alterar configurações administrativas.
- Ações de backup/restauração e saúde devem permanecer indisponíveis até seus serviços reais existirem no ambiente sombra.
- Nenhuma configuração do Shadow pode ser escrita no banco ou na nuvem de produção.

## 3. Situação observada no Shadow

Na inspeção anterior da navegação Shadow, os módulos `compras_consumo` e `configuracoes` ainda não constavam entre as entradas operacionais. O backend também não tinha routers dedicados a esses dois módulos. A interface Shadow atual é uma estrutura inicial, e não uma implementação equivalente dessas áreas.

O Shadow já possui autorização granular, auditoria e serviços de armazenamento em memória/PostgreSQL isolado. Esses mecanismos podem servir de base, mas não substituem os serviços específicos de configuração nem o serviço de leitura do relatório.

## 4. Sequência segura de implementação

1. Fechar o contrato de leitura de Acerto de Estoque e Estoque; verificar os nomes reais de campos no Shadow antes de codificar o relatório.
2. Implementar o serviço de domínio de Compras x Consumo e seus testes unitários, mas aguardar autorização do usuário antes de executar qualquer teste.
3. Expor endpoint somente leitura com capacidade explícita e sem mutação de saldo.
4. Implementar filtros, KPIs, evolução, tabela, impressão e exportação CSV no frontend Shadow.
5. Implementar configurações persistentes de módulos no backend, com trilha de auditoria e capacidade administrativa.
6. Construir a tela de Configurações com estados reais; deixar backup, IA, diagnóstico e sincronização marcados como indisponíveis até estarem concluídos.
7. Atualizar matriz de equivalência e critérios de aceite. Não publicar nem migrar dados.

## 5. Pendências que não devem ser presumidas

- Se os enums e formatos de `tipo` e `motivo` no Shadow são idênticos aos da produção.
- Se os repositórios Shadow de estoque/acertos contêm todos os campos exigidos pelo relatório.
- Se o valor unitário atual é suficiente para a regra contábil desejada para períodos históricos (é assim que a produção calcula hoje).
- Quais painéis transversais de Configurações serão implementados primeiro; não criar controles fictícios para recursos ainda ausentes.
