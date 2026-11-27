# Matriz de equivalência funcional — Bravo original x Bravo Shadow

## Objetivo e escopo

Esta matriz inicia a Fase 0 da migração híbrida e gradual. Compara o legado na branch `upgrade/project-hardening` com a versão sombra na branch `bravo-shadow`. É um inventário técnico inicial, não um aceite funcional nem autorização de corte.

**Regras de segurança:** o original é somente leitura; nenhuma escrita foi feita nele. Nenhuma base de produção foi consultada, conectada ou alterada. Não houve migração de dados, troca de tráfego ou alteração de autenticação/login.

## Baselines verificadas nesta inspeção

| Artefato | Branch | Blob SHA |
|---|---|---|
| `index.html` original | `upgrade/project-hardening` | `873dbf37bbcf2082faa0444ac28cb9ca9f8ff21c` |
| `bravo-shadow/frontend/index.html` | `bravo-shadow` | `2dfc65b42c52eae90b14bfd272c0d99458a8749f` |
| `bravo-shadow/backend/app/main.py` | `bravo-shadow` | `421490608922cd01e84c7d544199723d994d831b1` |

O legado tem 2.838 linhas nesta baseline. O roteador de conteúdo do original contém renderizadores dedicados para os 15 domínios, incluindo `renderDashboardView`, `renderCondominioView`, `renderPlanoContasView`, `renderFinanceiroView`, `renderFormasMonetariasView`, `renderContasBancariasView`, `renderMoradoresView`, `renderFornecedoresView`, `renderEmpregadosView`, `renderCategoriasView`, `renderEstoqueView`, `renderAcertoEstoqueView`, `renderDocumentosView`, `renderUsuariosView` e `renderRelatoriosCentralView`.

No Shadow, os 15 domínios aparecem na navegação, mas a própria interface informa que os módulos ainda não executam operações de negócio, com exceção do fluxo de Formas Monetárias. A API registra routers para os domínios operacionais e possui endpoint agregado de leitura para Dashboard; a interface ainda não está integrada a ele.

## Legenda de situação

- **UI:** interface navegável / fluxo de tela.
- **API:** router e endpoints no backend.
- **Persistência:** adaptador PostgreSQL existente não equivale a migration aplicada nem a teste real de banco.
- **Paridade:** não declarar concluída até comparar campos, regras, permissões, dados e resultados do legado.

## Matriz inicial por módulo

| Módulo | Evidência no legado | Situação Shadow observada | Lacuna principal / dependência |
|---|---|---|---|
| Dashboard | `renderDashboardView`; gráficos de receitas/despesas, ocupação e estoque; funções de inicialização de gráficos | API possui `DashboardService` e endpoint agregado `/api/v1/dashboard/resumo`, protegido por `dashboard:read`; UI ainda precisa de integração e aceite | Definir métricas e filtros equivalentes; não exibir zeros fictícios nem converter falha de API em saldo zero |
| Condomínio & Conselho | `renderCondominioView`, `salvarDadosCondominio`, modal de conselheiro; dados institucionais, concessionárias e corpo diretivo | Tela Shadow própria com 17 campos institucionais e formulário/lista de conselho; formulários bloqueados até Google/Bearer; API GET/PUT singleton e CRUD de conselheiros; adapters PostgreSQL | Revisar auditoria transacional, concorrência do singleton e política de exclusão do conselho; mandato/atas/anexos não existem no contrato observado; integração e homologação pendentes |
| Plano de Contas | `renderPlanoContasView`; cadastro/edição com código, nome e tipo Receita/Despesa | Tela Shadow própria mapeada; campos desabilitados até sessão Google/Bearer; API CRUD, ETag na edição, código único e bloqueio de exclusão com referência financeira | Hierarquia e níveis sintético/analítico não existem no contrato observado; auditoria transacional do CRUD ainda precisa ser revisada; integração e homologação pendentes |
| Contas a Pagar / Receber | `renderFinanceiroView`; títulos e classificações | Navegação/placeholder; router e persistência no backend | Faltam no contrato Shadow datas/status/baixa e vínculo bancário necessários a vários relatórios; mapear regras reais antes de ampliar |
| Formas Monetárias | `renderFormasMonetariasView` | Primeiro fluxo Shadow conectado: listar, criar, editar e excluir via API | Validar equivalência de campos, duplicidade, impacto em registros existentes e comportamento de exclusão; único candidato a piloto de UI, ainda sem aceite |
| Contas Bancárias / Caixa | `renderContasBancariasView` | Navegação/placeholder; router e persistência no backend | Saldo atual é manual; esclarecer origem do saldo, conciliação, movimentações e vínculo com Financeiro |
| Moradores & Unidades | `renderMoradoresView`, `filtrarMoradoresBloco`, modal CRUD e importação CSV/TXT; bloco/apartamento, nome, e-mail, telefone, CPF/RG, pet e vaga | Tela Shadow própria com formulário, filtros, tabela e área de importação; campos e ações bloqueados até Google/Bearer; API CRUD + importação e adapter PostgreSQL | Importação backend não é atômica nem retorna erros por linha; parser legado não trata todos os CSVs com aspas; sem unicidade de unidade, paginação ou histórico de exclusão; dados pessoais exigem proteção |
| Fornecedores | `renderFornecedoresView`, modal CRUD; CNPJ e razão social | Tela Shadow própria com formulário, pesquisa e tabela; controles bloqueados até Google/Bearer; API CRUD e adapter PostgreSQL | Sem validação/duplicidade de CNPJ, exclusão física sem verificação de vínculos e sem If-Match no router; Admin e Operador possuem CRUD |
| Empregados | `renderEmpregadosView`; inclui contato de emergência | Navegação/placeholder; router e persistência no backend | Conferir dados funcionais e contato de emergência, acesso restrito e regras de atualização |
| Pastas & Categorias | `renderCategoriasView`; há também exclusão de motivo de acerto | Navegação/placeholder; routers separados para categorias e motivos de acerto | Confirmar se “pastas”, categorias e motivos são entidades distintas; mapear referências e bloqueios de exclusão |
| Estoque & Inventário | `renderEstoqueView`, visualização de foto, gráfico de status e processamento de foto compactada | Navegação/placeholder; router e persistência no backend | Comparar campos de produto, marca/linha/fabricante, fotos, códigos, quantidade, níveis, filtros e scanner; distinguir edição de metadados de movimentação |
| Acerto de Estoque | `renderAcertoEstoqueView`, busca/filtro de produtos e exclusão de acerto | Navegação/placeholder; router e persistência no backend | Preservar histórico imutável, motivos, cálculo de saldo e atomicidade entre movimento e estoque; auditoria é pré-requisito |
| Gestão de Documentos | `renderDocumentosView`, visualizar/baixar documento e processamento gzip | Navegação/placeholder; router e persistência no backend | Mapear formato gzip/base64, nome original, MIME, limites, visualização/download, categorias e estratégia de arquivos |
| Relatórios & DRE | `renderRelatoriosCentralView`; funções de relatório e integração de gráficos | Navegação/placeholder; não há API própria de relatórios/DRE | Definir fórmulas, períodos, competência/caixa, filtros, agrupamentos e reconciliação com Financeiro/Plano de Contas |
| Gestão de Usuários | `renderUsuariosView`; cadastro e administração legados | Navegação/placeholder; router existe, mas rotas de negócio seguem sem proteção | Separar cadastro, perfil e status; Google ID token; matriz de capacidades aprovada; provisionamento seguro do primeiro Admin |

## Componentes transversais identificados

1. **Persistência do legado:** o original inicializa cliente Supabase diretamente no frontend e contém funções de salvamento/carregamento. Antes de importar qualquer dado, identificar tabelas, chaves, políticas, relacionamentos, formatos e origem de cada coleção. Não reutilizar credenciais nem conectar Shadow ao projeto de produção.
2. **Arquivos:** o legado comprime arquivos/fotos em gzip e base64 no navegador e possui fluxos de visualizar/baixar. O Shadow preserva conteúdo comprimido em contratos existentes, mas não tem estratégia de armazenamento externo migrada.
3. **Importação/exportação:** há funções de exportação para CSV e importação de planilha de moradores. Esses fluxos precisam de especificação própria, incluindo erros por linha, duplicidade e reprocessamento.
4. **Navegação e estado:** o legado tem renderização de módulos, abas, modais e estado de filtros. O Shadow ainda possui navegação simples e um fluxo de Formas Monetárias.
5. **Autenticação e autorização:** o original tem telas/fluxos de login e primeiro acesso. O Shadow tem fundação de validação Google no backend, mas o Client ID não está configurado e as rotas de negócio não estão protegidas. Não ativar exposição pública nem introduzir senha local.
6. **Dashboard/DRE:** os resultados históricos não podem ser reproduzidos com segurança apenas com os campos financeiros atuais; faltam datas/status de liquidação e associação bancária. Regras e limitações estão detalhadas em `auditoria-dashboard-relatorios-dre.md`.

## Status geral desta fase

- [x] Baseline do original identificada e SHA registrado.
- [x] Lista dos 15 módulos confirmada no roteador do legado e na navegação Shadow.
- [x] Renderizadores e funções transversais mais relevantes identificados.
- [x] Diferença entre presença visual, API e persistência explicitada.
- [x] Fichas estáticas de coleções dos lotes 01 a 06 elaboradas: Condomínio/Conselho/Plano de Contas; Financeiro/Formas Monetárias/Contas Bancárias; Moradores/Fornecedores/Empregados; Categorias/Motivos; Estoque/Acertos; Documentos.
- [x] Principais incompatibilidades já identificadas nos seis lotes, incluindo preservação de IDs, datas históricas, movimentos de estoque, referências textuais e arquivos Gzip.
- [ ] Inventário completo de campos por tela e formulário para todos os módulos.
- [ ] Inventário de regras de negócio e validações por operação.
- [x] Mapa estrutural de coleções e dependências consolidado em `revisao-consolidada-dependencias-fase0.md`.
- [x] Conferência estática dos formulários e gravações do legado para os principais vínculos; evidências e linhas do código registradas em `evidencias-relacionamentos-legado-fase0.md`.
- [ ] Confronto do mapa com payload persistido autorizado, campos históricos e extensões da instalação ativa.
- [ ] Aprovação de política para órfãos, duplicidades e vínculos ambíguos.
- [ ] Inventário de relatórios, importações/exportações e formatos de arquivos.
- [ ] Matriz de permissões por operação aprovada.
- [ ] Critérios de aceite e reconciliação definidos por módulo.
- [ ] Testes executados e evidências registradas.

## Próxima sequência recomendada

1. Completar as fichas da Fase 0 para Dashboard/Relatórios/DRE e Gestão de Usuários, incluindo métricas, fórmulas, filtros, operações, permissões e dependências.
2. Confrontar as evidências de código com o payload autorizado e formalizar política de órfãos, duplicidades e vínculos ambíguos; não inferir cardinalidades ausentes.
3. Fazer especificação detalhada de um módulo cadastral de baixo risco, comparando cada formulário e ação com o contrato Shadow.
4. Validar localmente o backend e os adaptadores com banco descartável, depois de migrations e políticas revisadas.
5. Só então propor o piloto de importação com dados sintéticos/anonimizados, relatório de divergências e rollback ensaiado.

A CI da branch bravo-shadow executou build/smoke test Docker e 360 testes backend aprovados contra PostgreSQL descartável no run 45894322542. Essa evidência valida a suíte automatizada, mas não substitui a conclusão das fichas restantes, validação visual em navegador, revisão de segurança ou aceite funcional.

**Não é aceite de migração:** nenhuma linha desta matriz autoriza corte, escrita dupla, mudança de roteamento, migração de dados reais ou alteração do original. As descrições de campos e regras ainda precisam ser verificadas nos formulários e operações completos antes da implementação.


## Complemento de aceite — Dashboard/DRE e Gestão de Usuários

Esta seção complementa a matriz com critérios verificáveis derivados das auditorias estáticas específicas. Ela não representa aceite funcional nem liberação de rotas.

### Dashboard, Relatórios e DRE

**Estado confirmado:** a interface Shadow ainda não consulta indicadores reais. O backend possui `DashboardService` e `GET /api/v1/dashboard/resumo`, protegido por `dashboard:read`, com totais de títulos e diferença aritmética; isso não constitui uma DRE completa nem está integrado à interface. Não há router/serviço de relatórios por período ou DRE agrupada.

**Paridade legada que precisa ser preservada ou explicitamente revista:**
- totais gerais somam todos os títulos, sem filtro de período ou liquidação;
- Receber e Pagar são classificados pelo tipo do título;
- agrupamento por conta usa `planoContaId` existente;
- títulos sem conta entram nos totais gerais, mas não nas linhas por conta;
- o legado não valida correspondência entre tipo do título e tipo da conta;
- a diferença Receber menos Pagar não é saldo bancário conciliado.

**Critérios de aceite para primeira entrega Shadow:**
1. Serviço agregado somente de leitura, usando as fontes Financeiro e Plano de Contas existentes.
2. Totais separados de Receber e Pagar, diferença aritmética com nome explícito e quantidade de títulos.
3. Agrupamento por conta sem excluir títulos sem vínculo dos totais gerais.
4. Valores calculados com Decimal, sem conversão intermediária para float.
5. Estado vazio real distinto de falha de API; indisponibilidade nunca deve virar R$ 0,00.
6. Sem filtros por data, competência, vencimento, liquidação ou conciliação até aprovação de novos campos e regras.
7. Nenhuma exposição dos dados financeiros antes da autenticação e autorização efetivas.

**Bloqueios atuais:** interface sem integração com o endpoint agregado; matriz Admin/Operador ainda sem aprovação; contrato financeiro sem datas, status de liquidação ou conta bancária. Portanto, relatórios por período e saldo de caixa/banco permanecem fora do escopo.

Referência: `auditoria-dashboard-relatorios-dre.md`.

### Gestão de Usuários

**Estado confirmado:** o contrato Shadow modela perfil por e-mail, nome, loja, cargo, perfil e status; o armazenamento ainda é temporário em memória. Não existe integração Google/token/claims nem autorização efetiva nas rotas. O campo `perfil` ainda não é uma permissão aplicada.

**Regra de identidade obrigatória:** autenticação pela conta Google/e-mail verificado. Não transportar senha/hash legado, não criar login por senha local e não copiar credenciais de exemplo do HTML.

**Critérios de aceite antes de ativar o módulo:**
1. Validar token Google no servidor e exigir e-mail verificado.
2. Vincular a identidade autenticada a um único perfil interno ativo por e-mail normalizado.
3. Rejeitar e-mail duplicado e perfil inativo; não provisionar privilégios automaticamente a partir de claims não aprovados.
4. Aplicar matriz explícita de capacidades por módulo e ação; não confiar no texto do campo `perfil` isoladamente.
5. Proteger todas as rotas de usuários e impedir autoexclusão/remoção do último administrador ativo.
6. Auditar criação, alteração de perfil/status e desativação, sem registrar tokens ou segredos.
7. Definir primeiro administrador por procedimento controlado e aprovado, sem credenciais embutidas.
8. Testar token ausente/inválido/expirado, e-mail não verificado, usuário inexistente/inativo, duplicidade, privilégio insuficiente e último administrador.

**Bloqueios atuais:** integração Google não configurada, autorização não aplicada às rotas, persistência em memória e matriz de capacidades ainda não aprovada. A tela de login permanece fora desta etapa e não será redesenhada agora.

Referência: `auditoria-gestao-usuarios.md`.

### Situação atualizada da descoberta

- [x] Auditoria estática específica de Dashboard/Relatórios/DRE registrada e critérios mínimos de aceite detalhados.
- [x] Auditoria estática específica de Gestão de Usuários registrada e bloqueios de identidade/autorização detalhados.
- [x] Implementar serviço agregado e endpoint de resumo do Dashboard, protegido por `dashboard:read` e coberto por testes HTTP e unitários.
- [ ] Integrar a interface ao endpoint e implementar agrupamentos de DRE somente após aprovação de fórmulas e campos.
- [ ] Aprovar matriz de capacidades e procedimento do primeiro administrador.
- [ ] Integrar validação Google no servidor sem alterar a tela de login nesta fase.
- [ ] Executar testes de aceitação em navegador e persistência descartável após revisão das migrations/policies.

**Limite de evidência:** as duas auditorias são estáticas e baseadas no código versionado. Não houve execução de tela, consulta ao banco, conexão de produção, aplicação de migration ou validação com dados reais.


## Complemento de aceite — cadastros auxiliares e operacionais

Critérios derivados das auditorias estáticas existentes. Os itens abaixo organizam o que deve ser provado antes da integração; não aprovam regras adicionais nem liberam os endpoints atuais.

### Formas Monetárias e Contas Bancárias

**Contrato legado observado:** Formas Monetárias contém `id`, `nome`, `multaPct` (novo cadastro apresenta 2,0%). Contas Bancárias contém `id`, `banco`, `saldo` (novo cadastro apresenta 0). O saldo é informado manualmente; não existe histórico de movimentos nem vínculo com títulos financeiros. A multa não foi encontrada em uso no cálculo financeiro.

**Aceite mínimo:** preservar os campos e defaults observados; distinguir saldo informado de saldo calculado/conciliado; não criar relação entre forma monetária, banco e título sem decisão aprovada; testar criação, edição, exclusão, valores decimais e preservação de dados existentes.

**Bloqueio:** autorização HTTP ausente e persistência real não configurada. Não exibir saldo como conciliado e não inferir cobrança de multa.

Referência: `auditoria-formas-monetarias-contas-bancarias.md`.

### Fornecedores e Empregados

**Contrato legado observado:** Fornecedores contém `id`, `cnpj`, `razaoSocial`; CNPJ e razão social são obrigatórios no formulário. Empregados contém `id`, `nome`, `cargo`, `empresa`, `endereco`, `telefone`, `contatoEmergenciaNome`, `contatoEmergenciaTel`; apenas nome e cargo são obrigatórios.

**Aceite mínimo:** preservar exatamente os campos e obrigatoriedades; não introduzir validação matemática de CNPJ, unicidade, dados pessoais adicionais ou vínculos empregatícios presumidos; testar edição sem perda de propriedades previstas, busca/listagem, exclusão e controle de acesso a endereço/contatos.

**Bloqueio:** autorização HTTP e persistência não aprovadas. Não importar dados pessoais reais nesta fase.

Referência: `auditoria-fornecedores-empregados.md`.

### Moradores e Unidades

**Contrato legado observado:** cadastro de morador inclui bloco, apartamento, nome, e-mail, telefone, CPF/RG, pet e vaga. Bloco, apartamento e nome são obrigatórios. A importação legada admite cabeçalho com sinônimos e fallback posicional, mas o parser simples não garante CSV com delimitadores dentro de aspas nem XLSX real.

**Aceite mínimo:** preservar os campos, filtros textuais e busca sem distinção de caixa; parser de importação deve identificar formato real, tratar aspas/escapes, reportar linha inválida e não inserir duplicidades silenciosamente; prévia e relatório por linha devem preceder confirmação de lote; dados pessoais devem ser mascarados em logs e protegidos por capacidade específica.

**Bloqueio:** não importar arquivos reais até haver parser testado, política de duplicidade/unidade e autorização aprovada. O endpoint atual de lote recebe JSON estruturado, não upload de planilha.

Referência: `auditoria-moradores-unidades.md`.

### Pastas, Categorias e Motivos de Acerto

**Contrato legado observado:** ambos usam `id` e `nome`. Pastas são referenciadas por texto em `documentos.pasta`; motivos de acerto são gravados como texto em `acertos_estoque.motivo`, sem vínculo por ID demonstrado.

**Aceite mínimo:** preservar textos históricos; não criar FK artificial para motivo; ao evoluir pasta para ID estável, criar mapeamento explícito, contabilizar órfãos e manter leitura de documentos antigos; impedir exclusão que cause perda de classificação sem política aprovada.

**Bloqueio:** relação documental é textual e não há evidência de vínculo persistido por ID. Não executar normalização ou exclusão em massa.

Referência: `auditoria-pastas-categorias-motivos.md`.

### Segurança transversal das rotas

A auditoria estática identificou routers de negócio sem dependências de autenticação/autorização. O health check é a única exceção pública intencional, sem dados sensíveis.

**Bloqueio crítico comum:** nenhum endpoint de negócio deve ser considerado pronto para uso real ou exposto a dados sensíveis até validação do token Google no servidor, vínculo a perfil ativo e autorização por capacidade em cada ação. CORS, ocultação de telas e campo `perfil` não substituem esse controle.

Referência: `auditoria-rotas-autorizacao.md` e `matriz-roles-permissoes-revisao-migracao.md`.

### Situação desta rodada

- [x] Critérios de aceite para Formas Monetárias e Contas Bancárias registrados.
- [x] Critérios de aceite para Fornecedores e Empregados registrados.
- [x] Critérios de aceite para Moradores/Unidades e importação por arquivo registrados.
- [x] Dependências de Categorias/Pastas e Motivos explicitadas sem inventar relacionamentos.
- [x] Bloqueio transversal de autenticação/autorização destacado para todos os módulos.
- [ ] Aprovar a matriz funcional Admin/Operador por capacidade.
- [ ] Corrigir e testar autenticação/autorização nos routers antes de qualquer teste com dados sensíveis.
- [ ] Validar parser de planilhas com arquivos sintéticos representativos e relatório de prévia.
- [ ] Definir política de normalização de pastas e integridade de documentos históricos.

**Evidência:** auditoria estática dos contratos e telas versionadas; nenhum dado real foi consultado, nenhuma migration foi aplicada e nenhuma rota foi alterada nesta rodada.


## Atualização de segurança — política efetiva de capacidades

A matriz funcional Admin/Operador permanece sem aprovação. O código de autorização foi ajustado para que ambos os perfis tenham conjunto vazio de capacidades até aprovação formal. Portanto, autenticação Google válida e conta ativa não concedem acesso a operações de negócio por si só. A dependência central retorna 403 para ambos os perfis enquanto a matriz não for aprovada.

Esta correção não protege automaticamente os routers existentes: cada rota de negócio ainda precisa declarar dependências de autenticação e capacidade, e a validação completa deverá ocorrer em testes HTTP. Nenhum endpoint deve ser considerado liberado para dados reais nesta fase.


## Atualização de implementação — proteção HTTP por capacidade (26/11/2026)

A política de capacidades continua em modo deny-by-default: os perfis Admin e Operador não recebem permissões até aprovação explícita da matriz. Nesta rodada, a dependência central de autenticação Google + capacidade foi integrada diretamente aos endpoints abaixo:

| Router | Ações protegidas |
|---|---|
| `formas_monetarias` | read, create, update, delete |
| `categorias` | read, create, delete |
| `motivos_acerto` | read, create, delete |
| `conselheiros` | read, create, update, delete |
| `fornecedores` | read, create, update, delete |
| `empregados` | read, create, update, delete |
| `moradores` | read, create, update, delete, import |
| `usuarios` | read (lista e detalhe), create, update, delete |

Sem token autenticado, os endpoints protegidos retornam 401. Com identidade autenticada, mas sem capacidade aprovada, retornam 403. Os testes usam identidades sintéticas e validam o bloqueio dos perfis Admin e Operador; não concedem permissões a eles.

**Importante — Gestão de Usuários:** o cadastro interno continua sendo apenas o vínculo de perfil por e-mail. Não há senha local nem campo de senha aceito pelo schema. As rotas administrativas de usuários estão protegidas por capacidades, mas o procedimento de primeiro administrador e a matriz de permissões continuam pendentes. Não alterar a tela de login nesta fase.

**Limite da cobertura:** os routers de Condomínio, Plano de Contas, Financeiro, Contas Bancárias, Estoque, Acertos de Estoque, Documentos e demais domínios não listados nesta tabela ainda precisam de auditoria/proteção individual. A fundação central não protege automaticamente rotas que não declaram a dependência.

**Validação:** a suíte deve ser considerada pendente para o commit mais recente até que o GitHub Actions execute o SHA final. Nenhuma migration, política RLS, conexão de produção, importação real, dual-write ou cutover foi executado. A branch original permanece fora desta alteração.


## Atualização de segurança — Dashboard e Documentos (26/11/2026)

A inspeção dos routers confirmou que ambos os módulos já declaram dependências de capacidade por endpoint:

| Módulo | Operações protegidas | Observação |
|---|---|---|
| Dashboard | `dashboard:read` | Endpoint agregado somente leitura; testes cobrem 401, 403 e resposta agregada sem registros detalhados |
| Documentos | `documentos:read`, `documentos:create`, `documentos:update`, `documentos:delete` | Lista, detalhe, criação, edição e exclusão protegidos; conteúdo comprimido preservado pelo contrato |

A proteção HTTP não equivale a paridade visual ou aceite de negócio. A matriz Admin/Operador permanece deny-by-default. Os testes usam identidade sintética e overrides locais.

**Correção de CI:** a execução `45902519204` encontrou 1 falha em 421 testes: o teste de isolamento de Documentos criava instâncias FastAPI sem configurar a identidade sintética exigida pelo endpoint protegido. O teste foi ajustado para autenticar ambas as instâncias; nenhuma regra de produção foi relaxada. A nova execução vinculada ao commit corretivo deve ser verificada antes de declarar sucesso.

Nenhuma migration foi aplicada, nenhum dado real foi consultado/importado e o original permanece inalterado.


## Correção de auditoria — Dashboard/DRE (26/11/2026)

A revisão cruzada identificou descrições desatualizadas na documentação anterior. O código atual já contém `DashboardService`, `GET /api/v1/dashboard/resumo` e dependência `dashboard:read`. Os testes cobrem 401 sem identidade, 403 sem capacidade e retorno apenas de agregados quando a capacidade é habilitada no ambiente de teste.

O endpoint retorna contagens e totais agregados de títulos, calculados com `Decimal`. Ele não expõe os registros pessoais nem os textos de histórico. A interface Shadow ainda não está conectada ao endpoint. Não existe implementação completa de DRE, agrupamento por conta ou filtros por período.

A auditoria foi corrigida para separar explicitamente:
- Dashboard agregado existente no backend;
- integração visual ainda pendente;
- Relatórios/DRE ainda não implementados;
- matriz de perfis ainda deny-by-default.

A execução CI `45902675530` concluiu com sucesso para o commit corretivo `9e2d0f87656e58fcf1be282d5e93cae0823fce88`. As alterações documentais desta correção foram feitas depois dessa execução e ainda precisam de uma execução própria para serem cobertas pelo CI.


## Atualização do baseline de produção — 2026-11-27

A fotografia histórica acima foi complementada pela inspeção do `index.html` atualmente presente na branch `main`. A lista atual contém 17 módulos de navegação e recursos transversais adicionais de sessão Google, sincronização/offline, backup criptografado, histórico/saúde do sistema, IA, anexos, scanner, checklist, exportações e experiência PWA.

A baseline, os SHAs consultados, o estado atual da interface/API Shadow, as lacunas imediatas e os critérios de aceite estão registrados em **[baseline-paridade-producao-2026-11-27.md](baseline-paridade-producao-2026-11-27.md)**.

A partir desta data, a paridade deve ser medida contra essa baseline atual, não apenas contra a fotografia antiga da branch `upgrade/project-hardening`. O documento novo é um inventário estático; não representa homologação nem autorização de migração.


## Atualização de Configurações — API de estado dos módulos (27/11/2026)

O backend Shadow agora declara as capacidades `configuracoes:read` e `configuracoes:update`. Admin ativo recebe ambas; Operador ativo recebe somente leitura. As rotas protegidas são:
- `GET /api/v1/configuracoes/modulos` — `configuracoes:read`;
- `PATCH /api/v1/configuracoes/modulos/{key}` — `configuracoes:update`;
- `POST /api/v1/configuracoes/modulos/acao-em-massa` — `configuracoes:update`.

O catálogo contempla os 17 módulos da baseline. Ativar/desativar é apenas controle de visibilidade; não altera a matriz de autorização nem concede capacidades. Configurações não pode ser desativado. No PostgreSQL, alteração e evento de auditoria são gravados na mesma transação. No modo memória, a leitura usa defaults ativos e mutações são negadas por indisponibilidade de auditoria persistente.

Os testes sintéticos foram adicionados, mas não executados. A tela visual ainda não foi integrada. A tabela `module_settings` está somente no DDL rascunho/piloto; nenhum SQL foi aplicado.


## Empregados — atualização da paridade (27/11/2026)

O formulário legado inspecionado contém nome completo e cargo como obrigatórios; empresa, endereço, telefone, nome do familiar/contato de emergência e telefone de emergência como opcionais. A tabela exibe nome/função, empresa, endereço, telefone e contato de emergência, com ações de edição e exclusão. Não foi identificada importação neste módulo.

A Shadow possui schema, service, router e adapter PostgreSQL para os sete campos. Rotas: GET/POST/PUT/DELETE em `/api/v1/empregados`, protegidas por `empregados:read/create/update/delete`. Admin e Operador têm CRUD na matriz atual. O armazenamento PostgreSQL é ligado no construtor de serviços.

A interface visual foi adicionada à navegação Shadow, sem dados fictícios, sem chamadas de rede e com controles desabilitados até integração da autenticação Google/Bearer e API HTTPS isolada. Lacunas: exclusão física sem arquivamento ou verificação de referências; ausência de If-Match/ETag na API; listagem sem filtros/paginação; auditoria de CRUD não confirmada. Endereço e contatos são dados pessoais. Esta atualização é inventário estático, não homologação nem autorização de ativação.


## Estoque & Inventário — atualização da paridade (27/11/2026)

A inspeção do legado identificou painel com contagens de estoque adequado, crítico e excedente; filtro por situação; gráfico de status; tabela com foto, etiqueta/código, descrição, quantidade, mínimo/máximo, alerta e ações de edição/exclusão. O formulário legado básico inclui código/etiqueta, descrição, quantidade, mínimo, máximo e foto compactada Gzip/Base64. O contrato Shadow já contempla também marca, linha, fabricante, data de cadastro, setor, unidade, valor unitário, status, cor e referência da foto — incluindo os campos adicionais solicitados para rastrear a origem do produto.

A API Shadow possui GET/POST/PUT/DELETE em /api/v1/estoque, com capacidades estoque:read/create/update/delete. Quantidades suportam três casas decimais e valor unitário duas. O service impede alteração direta do saldo após movimentações e impede exclusão quando existem acertos vinculados; o saldo deve ser alterado pelo módulo Acerto de Estoque. O adapter PostgreSQL armazena os campos de produto e serializa a edição com bloqueio de linha.

A nova interface Shadow contempla cadastro ampliado, filtros/indicadores estruturais e tabela. Os controles permanecem desabilitados, sem chamadas de rede ou dados fictícios. Scanner, impressão de etiquetas, fotos/armazenamento externo, checklist, relatórios por setor e integração do histórico ainda não estão conectados. A listagem atual não possui filtros/paginação na API. Esta é uma entrega visual/documental, não homologação nem autorização de ativação.

## Acerto de Estoque — atualização da paridade (27/11/2026)

O legado apresenta histórico com data/hora, tipo, produto, quantidade, motivo e ação de exclusão; formulário de novo movimento com tipo Entrada/Saída, busca de produto por etiqueta/nome, quantidade e motivo. No legado, a exclusão remove o movimento sem recompor saldo, deixando risco de divergência.

A Shadow mantém GET/POST em /api/v1/acertos-estoque, protegidos por acertos_estoque:read/create. O catálogo de motivos é consultado em GET /api/v1/motivos-acerto-estoque. Admin e Operador têm leitura e criação. Quantidade é Decimal positiva com até três casas.

Na persistência PostgreSQL, o produto é bloqueado com SELECT FOR UPDATE; valida saldo não negativo; atualiza quantidade e insere histórico na mesma transação. Não há rotas PUT/DELETE; o service recusa exclusão e recomenda movimento compensatório. A interface Shadow foi adicionada com formulário, histórico e explicação de integridade, mas permanece desabilitada e sem chamadas de rede.

Lacunas: histórico/listagem sem filtros ou paginação; busca do produto e catálogo de motivos ainda não ligados à tela; scanner, anexos/evidências, aprovação e auditoria explícita do movimento não confirmados. O legado permitia apagar movimento sem recompor saldo; esse comportamento destrutivo não foi replicado.

## Usuários — atualização da paridade (27/11/2026)

O legado apresenta login, senha/redefinição local e CRUD de usuários com login, nome, e-mail, loja/unidade, cargo e ações de senha/edição/exclusão. Esses mecanismos de senha local e login próprio não serão migrados: o Bravo Shadow usa identidade Google e vincula e-mail verificado a um único usuário interno Ativo; perfil/capacidades são internos. Não há auto-cadastro.

A API Shadow possui leitura por GET, cadastro POST e atualização cadastral PUT. O cadastro comum força perfil Operador e status Ativo; atualização só altera nome, loja e cargo, sem trocar e-mail ou privilégios. DELETE retorna HTTP 410; desativação lógica é feita por POST /{id}/desativar, com auditoria na mesma transação PostgreSQL, sem auto-desativação e com proteção ao último Admin ativo.

Capacidades de usuários são restritas ao Admin; Operador não recebe usuarios:read/create/update/delete/deactivate. O método interno de alteração de perfil/status não está exposto por rota. A interface Shadow é apenas um painel de pré-requisitos, sem chamadas de rede nem controles de gestão ativos.

Pendências: ligar a UI à autenticação Google e API HTTPS; definir e documentar provisionamento inicial de Admin e aprovação de cadastro; decidir se/como expor alteração de perfil/status com autorização e auditoria; completar a interface administrativa após essas decisões. Não reintroduzir senha local, reset local ou auto-registro.

## Integração transversal — fundação HTTP (27/11/2026)

Adicionado `frontend/js/bravo-api.js`, cliente HTTP comum para futura comunicação com API Shadow. Valida HTTPS (exceto localhost), restringe caminhos a `/api/v1/`, injeta Bearer fornecido pela sessão em memória, não usa cookies, cache ou redirects e padroniza erro/request ID.

Ainda não integrado ao HTML/telas. Bloqueios objetivos: API HTTPS isolada inexistente; CORS do FastAPI permanece fechado; URL do preview Shadow não definida; backend seleciona memória por padrão e precisa de PostgreSQL explicitamente configurado para persistência; Google Client ID/origens precisam ser configurados por ambiente. Não habilitar módulos até resolver estes itens sem tocar na produção.

## Preparação de container e isolamento de hospedagem

O `Dockerfile` foi endurecido para hospedagem Shadow: imagem Python 3.12 slim, usuário sem privilégios, frontend estático incluído e inicialização bloqueada a menos que `BRAVO_STORAGE_BACKEND=postgres`, `BRAVO_DATABASE_URL` e `GOOGLE_CLIENT_ID` estejam definidos. A porta usa `PORT` do provedor ou 8000. `.env.example` contém apenas placeholders e `.dockerignore` já exclui `.env`, diretórios Git e artefatos locais.

O Worker Cloudflare de prova agora está com `workers_dev=false`, origem CORS de placeholder não utilizável e validação de `azp` quando presente no ID token. Isso é apenas configuração de segurança; nenhum Worker foi publicado.

### Limitações que continuam impedindo hospedagem

- O FastAPI ainda não implementa middleware CORS/allowlist. Definir variável no ambiente não habilita CORS; permanece fechado.
- Não existe provedor/origem HTTPS isolada aprovado ou configurado.
- Não existe PostgreSQL Shadow provisionado; não preencher secrets com dados de produção.
- O Dockerfile é blueprint; não foi construído nem publicado.