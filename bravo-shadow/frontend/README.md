# Frontend — identidade visual Bravo Shadow

## Direção visual

A interface deve ser reconhecível como Bravo: modo noturno fixo, visual profissional e navegação integrada. A evolução será de refinamento, não uma ruptura de identidade.

## Tokens iniciais

| Token | Valor | Uso |
|---|---|---|
| Fundo principal | #111315 | Fundo geral |
| Superfície 1 | #191d20 | Sidebar e painéis |
| Superfície 2 | #202529 | Cards e áreas elevadas |
| Superfície 3 | #272e33 | Hover e controles |
| Texto principal | #edf1f3 | Títulos e dados |
| Texto secundário | #c2cbd0 | Conteúdo de apoio |
| Texto suave | #929da4 | Metadados |
| Borda | #343d43 | Separadores |
| Borda forte | #465159 | Contornos de destaque |
| Acento | #36b7a5 | Ações e estados ativos |

## Regras de experiência

- Modo noturno fixo, sem alternância para tema claro.
- Sidebar, dashboard, abas e área de trabalho devem compartilhar a mesma linguagem visual.
- Uma única navegação global e um único workspace; módulos são áreas internas da mesma aplicação.
- Cards, tabelas, filtros, formulários, modais e estados vazios devem reutilizar tokens e componentes.
- Hierarquia tipográfica clara, espaçamento consistente e animações discretas.
- Responsividade para desktop, tablet e celular.
- Foco visível, contraste adequado e navegação por teclado.
- Evitar fundos brancos, gradientes decorativos excessivos e duplicação de cabeçalhos/abas.

## Estado

Este documento define o contrato visual. A interface será construída após o inventário de fluxos e componentes do original, evitando criar telas fictícias ou controles sem funcionalidade.

## Primeiro módulo conectado à API

O backend do módulo **Formas Monetárias** possui rotas protegidas de consulta, cadastro, edição e exclusão. A tela Shadow foi deliberadamente bloqueada até a integração do ID token Google: a implementação anterior fazia chamadas sem enviar `Authorization: Bearer`, o que não satisfaz o contrato de autenticação. Nenhuma chamada é disparada pela tela atual; nome e multa (0–100%, até duas casas) são apresentados como campos desabilitados.

O backend deste módulo ainda utiliza armazenamento em memória. Os registros são exclusivos do processo do ambiente sombra e são perdidos quando ele reinicia. Isso não é persistência definitiva nem integração com o banco de produção.

Os demais módulos continuam identificados como estrutura visual até que seus contratos e fluxos sejam conectados individualmente.

## Dashboard — integração de leitura preparada

A tela inicial está conectada ao evento de sessão autenticada do bootstrap. Quando o servidor confirmar a conta Google e o cadastro ativo, o bootstrap entrega ao Dashboard um cliente HTTP limitado, sem expor nem persistir o ID token. O Dashboard consulta somente `GET /api/v1/dashboard/resumo`, que exige a capacidade `dashboard:read`.

Os indicadores exibidos correspondem aos campos reais do contrato: quantidades de títulos a receber/pagar, valores agregados, diferença, produtos, moradores, documentos, contas do plano, fornecedores e empregados. Valores monetários são formatados em BRL; valores ausentes ou inválidos permanecem como traço. Erros HTTP 401 e 403 são apresentados como sessão expirada/não autorizada ou ausência de capacidade, nunca como zero.

A consulta é somente leitura, cancela requisições obsoletas ao trocar de módulo ou encerrar a sessão e atualiza apenas a tela do Dashboard. Não foram criados dados demonstrativos, indicadores sem suporte no backend, nem chamadas a APIs externas ou de produção. O contrato atual ainda não fornece inadimplência, vencidos, fluxo de caixa, séries temporais, alertas ou comparativos; esses itens continuam fora da tela funcional.

**Estado atual:** integração do Dashboard implementada no código, mas não ativada em produção/homologação. Continua dependendo de uma API Shadow hospedada em HTTPS, configuração explícita do bootstrap e concessão da capacidade `dashboard:read`.

## Autenticação Google — módulo cliente preparado, bootstrap pendente

A decisão confirmada para o Bravo Shadow é usar autenticação Google diretamente, sem Supabase Auth e sem login por senha local.

O módulo `js/google-auth.js` **já existe** e:
- carrega o Google Identity Services;
- recebe o ID token em memória;
- consulta `GET /api/v1/auth/me` com Bearer token;
- só aceita usuário que a API confirme como cadastrado e ativo;
- não grava token em `localStorage`, `sessionStorage` ou cookies;
- não concede perfil nem permissões no navegador.

**O módulo ainda não está conectado à tela.** A página `index.html` não importa esse módulo nem apresenta o botão Google. O bootstrap foi mantido desligado porque ainda não existe uma URL HTTPS de API hospedada e validada para o ambiente sombra. O GitHub Pages hospeda apenas arquivos estáticos; não executa FastAPI nem PostgreSQL. Não apontar o frontend para a API de produção.

O Client ID OAuth público já foi informado e está configurado no artefato de prova do Worker. Ele pode ser publicado no frontend; o Client Secret nunca deve ser incluído em HTML, JavaScript ou repositório. Ainda é necessário conferir as origens JavaScript autorizadas no projeto Google OAuth antes de ativar o botão.

No servidor, a API valida assinatura, emissor, audiência e expiração do ID token com `google-auth`, exige e-mail verificado e vincula a identidade a um único cadastro interno ativo. Usuário desconhecido, inativo ou duplicado é recusado. O perfil vem do cadastro Bravo, não dos dados declarados pelo navegador.

A tela de login original permanece intocada.

## Gestão de Usuários — estado da interface

A navegação da Gestão de Usuários apresenta um painel de pré-requisitos, sem botões de cadastro, edição ou desativação enquanto a sessão Google do navegador não estiver conectada e a matriz de permissões continuar fechada. O painel identifica separadamente:

- sessão Google do navegador ainda não conectada;
- consulta bloqueada pela ausência de `usuarios:read`;
- cadastro/edição sem capacidades concedidas;
- desativação lógica protegida por `usuarios:deactivate` ainda não concedida;
- exclusão física desabilitada pela API (HTTP 410).

Esse estado é intencional: a interface não consulta nem altera usuários com identidade ausente, não inventa dados e não concede permissões por perfil. Para avançar, é necessário configurar a URL HTTPS da API e aprovar explicitamente a matriz de permissões. A tela de login original permanece intocada.

## Acessibilidade da navegação

O frontend inclui atalho de teclado para pular diretamente ao conteúdo principal, indicador de foco visível para links e botões e uma região de conteúdo com anúncios educados para leitores de tela durante a troca de módulos. O atalho fica oculto visualmente até receber foco.

## Preview visual do Bravo Shadow — publicação bloqueada

O preview precisa ter origem e endereço independentes da aplicação original. **Não publicar esta pasta no GitHub Pages deste repositório enquanto isso puder substituir ou compartilhar o endereço de produção** `https://bravopinhais.github.io/bravopinhais/`.

- O endereço de produção acima não é um endereço válido para homologação do Shadow.
- O workflow `.github/workflows/bravo-shadow-pages.yml` não deve ser usado para publicar no endereço de produção.
- Ainda não existe URL pública de preview Shadow confirmada.
- O GitHub Pages hospeda apenas arquivos estáticos. Não executa FastAPI nem PostgreSQL e, sozinho, não habilita autenticação nem permissões.
- Antes de qualquer publicação, será necessário escolher e validar um destino independente, gratuito e sem afetar o original. Nenhum deploy está autorizado por esta documentação.

### Verificações antes de uma futura publicação

A publicação só poderá ser considerada após confirmar que o destino é distinto do domínio/caminho de produção, que a interface não chama APIs de produção, que não contém dados reais nem segredos e que as verificações automatizadas de segurança passaram. Até lá, o artefato permanece apenas na branch `bravo-shadow`.


## Endurecimento do cliente Google — 2026-11-27

O módulo `js/google-auth.js` recebeu uma revisão defensiva sem ativar o bootstrap da tela:

- o carregamento do Google Identity Services agora tem timeout de 15 segundos e remove listeners ao concluir, evitando Promise pendente indefinidamente;
- URLs de API com usuário/senha, query string ou fragmento são rejeitadas;
- o Client ID é validado no formato público OAuth do Google;
- cada tentativa de autenticação recebe um identificador sequencial e aborta a consulta anterior;
- uma resposta atrasada de uma tentativa anterior não pode substituir a sessão mais recente;
- encerramento/descarte da sessão aborta a consulta em andamento e invalida callbacks atrasados.

Esses controles melhoram a robustez do cliente, mas **não significam que o login esteja ativo**. O bootstrap permanece desligado até existir uma API HTTPS isolada e validada, origem frontend independente e aprovação da configuração OAuth. Nenhuma API de produção deve ser usada como fallback.

Não foram executados testes JavaScript ou workflows nesta etapa, conforme orientação de não executar testes por enquanto.


## Configurações — API preparada, interface pendente

O backend oferece `GET /api/v1/configuracoes/modulos`, `PATCH /api/v1/configuracoes/modulos/{key}` e `POST /api/v1/configuracoes/modulos/acao-em-massa`. Admin ativo pode alterar visibilidade; Operador pode apenas consultar. A interface ainda não consome esses endpoints porque o bootstrap Google/API HTTPS segue desligado. Não exibir toggles operacionais como se estivessem persistidos enquanto a sessão e a API não estiverem conectadas.


## Tela de Configurações — primeira estrutura visual

A navegação principal e o dashboard agora incluem acesso à tela de Configurações. A tela apresenta o catálogo dos 17 módulos, separação por grupo e as ações administrativas previstas. Os controles de ativação em massa permanecem desabilitados e os estados são identificados como aguardando API: não são valores carregados nem simulam persistência.

A interface não envia alterações porque ainda não existe sessão Google conectada ao frontend nem API HTTPS isolada configurada. A próxima integração deverá carregar `GET /api/v1/configuracoes/modulos` com o token da sessão e habilitar controles somente conforme as capacidades retornadas/permitidas pelo backend. O backend continua sendo a autoridade; Operador só consulta e Admin altera.


## Navegação funcional mapeada

A navegação Shadow agora inclui também `Compras x Consumo`, alinhada ao catálogo de 17 módulos da baseline. O item abre a estrutura do módulo, mas ainda não representa a tela de relatório concluída. A tela de Configurações permanece em modo seguro: não consulta nem altera estados enquanto não houver URL HTTPS isolada da API e sessão Google validada no navegador.


## Compras x Consumo — primeira interface do relatório

A navegação abre agora um painel próprio com filtros previstos no contrato da API (período, setor, busca, ordenação e opções de classificação), indicadores de compras/consumo/perdas/alertas, evolução mensal e detalhamento por produto. A interface não inventa valores nem simula gráficos ou resultados.

Os controles permanecem desabilitados até a integração segura da sessão Google no navegador. O backend expõe consulta protegida por `relatorios:read` e exportação CSV; a interface visual ainda não está conectada a esses endpoints. Impressão/PDF e renderização de dados reais continuam pendentes. O GitHub Pages estático não hospeda a API FastAPI.


### Compras x Consumo — renderização preparada

A interface agora contém funções de apresentação que validam a estrutura básica da resposta da API, formatam quantidades e valores em pt-BR, montam a query string dos filtros e renderizam indicadores, evolução mensal e detalhamento por produto usando escape de HTML para textos recebidos. Os alvos de renderização estão identificados na tela.

Essas funções são preparação de integração: não foram conectadas a uma sessão Google, não fazem chamadas de rede e não habilitam os controles. A consulta e a exportação continuam bloqueadas até existir uma API HTTPS Shadow independente e uma sessão autenticada com `relatorios:read`. Nenhum dado de exemplo é apresentado como real.


### Pastas & Categorias — estrutura de interface

A tela do módulo foi separada em duas áreas funcionais: pastas/categorias de documentos e motivos de acerto de estoque. Cada área apresenta formulário de cadastro, tabela de registros e estado vazio explícito. A documentação da tela informa a regra de proteção contra exclusão de categorias referenciadas por documentos e de motivos referenciados por movimentos de estoque.

Os formulários e ações permanecem desativados enquanto a sessão Google e a API HTTPS Shadow não estiverem integradas. As rotas de consulta/cadastro já existem no backend (`/api/v1/categorias` e `/api/v1/motivos-acerto-estoque`); não foi criada chamada de rede sem token, nem foram exibidos dados fictícios.


## Gestão de Documentos — primeira estrutura visual

A navegação abre uma tela própria para o módulo documental, com campos de pasta/categoria, título e arquivo, além de busca, filtro por pasta e tabela com nome do arquivo e ações previstas. A interface registra o fluxo observado no legado: inserir/substituir arquivo Gzip/Base64, visualizar e baixar documentos.

A tela permanece desabilitada e não envia arquivos enquanto não houver sessão Google integrada e API HTTPS Shadow isolada. A API atual oferece consulta, cadastro, edição e exclusão protegidos por capacidades, mas o conteúdo Gzip/Base64 ainda é armazenado diretamente no registro PostgreSQL. Não há nesta etapa armazenamento externo, URLs assinadas, pré-visualização por MIME, gestão de órfãos ou otimização de arquivos. Esses recursos não são presumidos como concluídos.

A implementação visual não define ainda limite de tamanho, allowlist de tipos, verificação de conteúdo, política de retenção nem estratégia de storage. Esses requisitos precisam ser fechados antes de habilitar upload. Nenhum dado real ou arquivo foi carregado e nenhum teste foi executado.


## Relatórios & DRE — primeira estrutura visual

A navegação abre uma tela própria para o Demonstrativo do Resultado do Exercício, com período, seleção de plano de contas, resumo de receitas/despesas/resultado líquido e detalhamento separado por contas de receita e despesa. Os comandos de consulta e exportação permanecem desabilitados até integração real.

### Regra legada observada

A implementação de produção inspecionada consolida os lançamentos financeiros classificados como `Receber` e `Pagar`, agrupa valores por `planoContaId` e apresenta as contas do Plano de Contas separadas por tipo `Receita` e `Despesa`. O resultado líquido é calculado como total de receitas menos total de despesas. A tela legada não apresenta filtro de período nessa função.

### Lacunas para a paridade

Não foi encontrado um router dedicado de relatórios no backend Shadow. A interface ainda não consulta API. Antes de implementar o cálculo, é necessário definir com precisão:
- se a DRE considera títulos lançados, pagos/recebidos ou ambos, e qual data determina o período;
- tratamento de cancelados, estornos, inadimplência e pagamentos parciais;
- inclusão/exclusão de contas sem movimento, subcontas e lançamentos sem plano vinculado;
- agrupamento por competência ou caixa, e consistência com os totais do módulo Financeiro;
- exportação PDF/Excel, filtros e trilha de auditoria da consulta.

Nenhum total fictício é exibido. O backend, os filtros e as exportações não foram declarados concluídos; não houve execução de testes nem acesso a dados de produção.


## Dashboard Executivo — ampliação da estrutura visual

A tela inicial foi reorganizada em quatro blocos: indicadores executivos, visão financeira, acesso rápido aos módulos e panorama operacional, além de uma área explícita para alertas e acompanhamento. O layout não apresenta valores simulados e mantém os estados como indisponíveis até autenticação e conexão com a API Shadow.

### Contrato real atualmente disponível

O endpoint protegido `GET /api/v1/dashboard/resumo` retorna:
- quantidades de formas monetárias, contas do plano, títulos financeiros, produtos, moradores, fornecedores, empregados e documentos;
- quantidade e valor agregado de títulos classificados como `Receber` e `Pagar`;
- diferença entre o valor a receber e o valor a pagar.

A tela separa os campos existentes dos indicadores que ainda exigem serviços específicos. O endpoint não entrega séries temporais, vencimentos, inadimplência, fluxo de caixa, alertas de estoque, pendências de sincronização ou gráficos. Esses dados não são calculados no navegador nem apresentados como se estivessem disponíveis.

O resumo atual percorre os serviços de listagem e agrega valores na camada de serviço. Antes de conectar em escala, é necessário avaliar agregações SQL, paginação/contagens eficientes e consistência transacional, evitando carregar coleções completas de documentos e demais registros apenas para contar.

A tela continua sem bootstrap Google/API HTTPS, e nenhum request é disparado. Nenhum dado de produção é consultado.


## Financeiro — Contas a Pagar / Receber

A navegação agora abre uma tela própria para lançamentos financeiros, alinhada ao fluxo observado no legado: tipo (Receber/Pagar), conta do Plano de Contas, histórico e valor. A lista apresenta as mesmas colunas e ações previstas. A tela também documenta o controle de versão ETag/If-Match do endpoint de edição.

Os campos, filtros, gravação e ações permanecem desabilitados até existir sessão Google conectada e API HTTPS Shadow independente. A tela não carrega dados de produção, não inventa títulos e não dispara chamadas sem token. O filtro visual é apenas estrutura e ainda não corresponde a filtro suportado pelo endpoint atual.

### Contrato backend existente

- `GET /api/v1/financeiro` — lista títulos; requer `financeiro:read`.
- `POST /api/v1/financeiro` — cria título; requer `financeiro:create`.
- `PUT /api/v1/financeiro/{id}` — atualiza com `If-Match` e versão; requer `financeiro:update`.
- `DELETE /api/v1/financeiro/{id}` — exclusão física; requer `financeiro:delete`.

O contrato atual possui apenas tipo, vínculo opcional com Plano de Contas, histórico, valor e versão. Não há datas de vencimento/competência, liquidação, pagamentos parciais, recorrência, baixa ou conciliação. A exclusão física exige uma política explícita de confirmação e auditoria antes de habilitar a ação na interface.

O serviço tem adapters em memória e PostgreSQL; o modo padrão da API continua em memória, e PostgreSQL só é selecionado por configuração explícita. A integração de sessão e a persistência hospedada seguem pendentes.


## Contas Bancárias / Caixa

A navegação abre agora uma tela própria para o módulo, alinhada ao contrato observado no legado e no backend: identificação do banco e saldo informado, com listagem das contas. A tela distingue explicitamente saldo informado de saldo conciliado ou calculado.

Os controles de cadastro permanecem desabilitados até integração com sessão Google e API HTTPS Shadow. Não são disparadas chamadas e nenhuma conta de exemplo é exibida.

### Contrato existente

- `GET /api/v1/contas-bancarias` — consulta, capacidade `contas_bancarias:read`.
- `POST /api/v1/contas-bancarias` — cadastro, capacidade `contas_bancarias:create`.
- `PUT /api/v1/contas-bancarias/{id}` — atualização, capacidade `contas_bancarias:update`.
- `DELETE /api/v1/contas-bancarias/{id}` — exclusão física, capacidade `contas_bancarias:delete`.

O schema contém somente `banco` e `saldo` (Decimal com duas casas), além do identificador. A matriz atual permite ao perfil Operador somente leitura neste módulo; Admin possui as capacidades cadastradas.

O contrato não representa extrato, caixa operacional, movimentações, transferências, conciliação, fechamento ou saldo calculado. A exclusão física também não verifica vínculos. Esses recursos não devem ser sugeridos como disponíveis até sua implementação e validação.


## Formas Monetárias — bloqueio preventivo da interface

O contrato legado contém nome e percentual de multa. O backend Shadow expõe:

- `GET /api/v1/formas-monetarias` — `formas_monetarias:read`.
- `POST /api/v1/formas-monetarias` — `formas_monetarias:create`.
- `PUT /api/v1/formas-monetarias/{id}` — `formas_monetarias:update`.
- `DELETE /api/v1/formas-monetarias/{id}` — `formas_monetarias:delete`.

O schema aceita multa de 0 a 100%, com no máximo duas casas decimais. O perfil Operador tem leitura; alterações são restritas ao perfil Admin.

A tela foi colocada em modo somente visual porque o helper anterior fazia `fetch` sem o cabeçalho `Authorization: Bearer`. A autenticação Google ainda não está conectada ao frontend; portanto, não se deve tentar contornar a proteção nem habilitar os formulários.

A persistência PostgreSQL possui adapter, mas o modo padrão continua sendo memória. Sem selecionar e provisionar PostgreSQL no ambiente isolado, os registros são voláteis. O serviço também não implementa verificação de referências antes da exclusão nem auditoria transacional específica. A integração financeira do percentual de multa ainda precisa ser confirmada no domínio de títulos.


## Plano de Contas

A tela Shadow agora representa o fluxo do legado: código, nome da conta e tipo Receita/Despesa, com listagem ordenada por código e filtros visuais previstos. Os campos permanecem desabilitados até a autenticação Google ser integrada; não há chamadas de API nem dados fictícios.

### Contrato existente

- `GET /api/v1/plano-contas` — `plano_contas:read`.
- `POST /api/v1/plano-contas` — `plano_contas:create`.
- `PUT /api/v1/plano-contas/{id}` — `plano_contas:update`, exige `If-Match` / ETag.
- `DELETE /api/v1/plano-contas/{id}` — `plano_contas:delete`.

Código (1–30 caracteres) e nome (2–160 caracteres) são obrigatórios; tipo é Receita ou Despesa. O serviço verifica duplicidade de código e o PostgreSQL possui proteção de unicidade. A exclusão depende de verificação de títulos financeiros vinculados e retorna conflito quando há referências. O perfil Operador tem leitura; escrita é restrita ao Admin.

O contrato não possui hierarquia de contas, conta-pai, centro de custo, níveis sintético/analítico ou natureza adicional. A API usa versionamento otimista para edição. Auditoria transacional específica de CRUD não foi confirmada; não habilitar gravações antes da revisão de auditoria e integração segura.


## Condomínio & Conselho

A tela Shadow agora apresenta os campos institucionais existentes no schema do condomínio e o cadastro do corpo diretivo. Os formulários e ações permanecem desabilitados até a integração Google/Bearer; não há requests automáticos, valores de exemplo ou leitura da produção.

### Condomínio

- `GET /api/v1/condominio` — `condominio:read`.
- `PUT /api/v1/condominio` — `condominio:update`.

Campos: nome, CNPJ, razão social, endereço, bairro, cidade, UF, CEP, telefone, e-mail, identificadores Copel dos blocos 1–4 e áreas comuns, registro de gás do salão e matrícula Sanepar.

### Conselho

- `GET /api/v1/conselheiros` — `conselheiros:read`.
- `POST /api/v1/conselheiros` — `conselheiros:create`.
- `PUT /api/v1/conselheiros/{id}` — `conselheiros:update`.
- `DELETE /api/v1/conselheiros/{id}` — `conselheiros:delete`.

Campos: nome, cargo, Bloco/Ap e telefone. Admin possui CRUD; Operador somente leitura.

Há adapters PostgreSQL para os dois cadastros, mas o serviço atual não implementa auditoria de negócio transacional específica. A atualização do singleton do condomínio não expõe If-Match/versão no contrato HTTP. Não habilitar gravações até revisar auditoria e concorrência.


## Moradores & Unidades

A tela Shadow apresenta cadastro, filtros, tabela e área de importação, sem realizar chamadas nem exibir dados pessoais fictícios. Todos os campos e ações permanecem desabilitados até a integração Google/Bearer com API HTTPS isolada.

### Contrato da API

- `GET /api/v1/moradores?bloco=&busca=` — `moradores:read`.
- `POST /api/v1/moradores` — `moradores:create`.
- `PUT /api/v1/moradores/{id}` — `moradores:update`.
- `DELETE /api/v1/moradores/{id}` — `moradores:delete`.
- `POST /api/v1/moradores/importar` — `moradores:import`.

Campos: bloco, apartamento e nome obrigatórios; e-mail, telefone, CPF/RG, pet e vaga de garagem opcionais. Admin e Operador possuem as capacidades de CRUD e importação no catálogo atual.

### Importação e limites

O legado aceita CSV/TXT e procura cabeçalhos equivalentes a bloco, apartamento/unidade, nome, e-mail, telefone, CPF/RG, pet e vaga. O backend recebe lote JSON. O serviço atual insere os registros sequencialmente, sem atomicidade garantida nem relatório de falhas por linha. O parser legado divide colunas por vírgula ou ponto e vírgula de forma simples e não trata corretamente todos os CSVs com campos entre aspas contendo separadores.

Não habilitar a importação antes de adicionar prévia, validação, deduplicação, limites de lote, resultado por linha e garantia transacional. A API também lista toda a coleção antes de aplicar filtros e não expõe paginação. Não há unicidade relacional de unidade nem histórico de exclusão demonstrados no contrato atual.

CPF/RG e contatos são dados pessoais. Não utilizar dados reais em homologação; limitar acesso, logs e exportações conforme a política do condomínio.


## Fornecedores

A tela Shadow apresenta cadastro, pesquisa e tabela de fornecedores com os dois campos identificados no legado: CNPJ e Razão Social. Campos e ações ficam desabilitados até integração da sessão Google/Bearer com API HTTPS isolada. Não há dados fictícios nem chamadas automáticas.

### Contrato da API

- `GET /api/v1/fornecedores` — `fornecedores:read`.
- `POST /api/v1/fornecedores` — `fornecedores:create`.
- `PUT /api/v1/fornecedores/{id}` — `fornecedores:update`.
- `DELETE /api/v1/fornecedores/{id}` — `fornecedores:delete`.

Campos obrigatórios: `cnpj` e `razaoSocial`. O schema remove espaços nas extremidades e recusa campos extras. Admin e Operador possuem CRUD no catálogo de permissões atual.

### Limites que impedem ativação imediata

O serviço atual não valida CNPJ nem detecta duplicidade. O repositório PostgreSQL não evidencia índice único por CNPJ. A exclusão é física e não há verificação de vínculos com compras ou outros registros. Embora o adapter incremente uma versão interna em atualizações, o router não exige If-Match/ETag. O contrato não contém contato, endereço, inscrição estadual ou dados bancários; não presumir esses campos sem confirmar o legado.


## Empregados

A interface Shadow do módulo Empregados foi criada com os campos do formulário legado: nome completo, função/cargo, empresa, endereço, telefone, nome do contato de emergência e telefone de emergência. Nome e cargo são obrigatórios; os demais são opcionais. A tela não apresenta registros fictícios e mantém formulário, pesquisa e ações desabilitados até integração segura da sessão Google/Bearer com API HTTPS isolada.

### Contrato da API

- `GET /api/v1/empregados` — `empregados:read`.
- `POST /api/v1/empregados` — `empregados:create`.
- `PUT /api/v1/empregados/{id}` — `empregados:update`.
- `DELETE /api/v1/empregados/{id}` — `empregados:delete`.

O schema remove espaços nas extremidades e recusa campos extras. Admin e Operador possuem CRUD no catálogo atual de permissões. O armazenamento PostgreSQL persiste os sete campos de cadastro e incrementa versão interna na edição.

### Limites que impedem ativação imediata

A exclusão atual é física, sem fluxo de desligamento/arquivamento ou verificação de referências. O router não exige If-Match/ETag apesar da versão interna no repositório. A listagem retorna a coleção inteira, sem filtros ou paginação. Não foram identificados no formulário legado campos de salário, documentos, jornada ou vínculo trabalhista; não devem ser acrescentados sem validação funcional. Endereço e contatos, especialmente o contato de emergência, exigem restrição de acesso e minimização de exposição.


## Estoque & Inventário

A interface Shadow foi criada para o cadastro de produtos e consulta de inventário, preservando os campos do contrato atual: item, etiqueta/código, quantidade, mínimo, máximo, foto (nome e conteúdo Gzip/Base64), marca, linha, fabricante, data de cadastro, setor, unidade, valor unitário, status, cor e referência da foto. Inclui estrutura visual para indicadores de estoque adequado/crítico/excedente, filtros e tabela de inventário. Controles permanecem desabilitados até integração segura Google/Bearer e API HTTPS isolada; não há dados fictícios nem chamadas de rede.

### Contrato e regras atuais

- GET /api/v1/estoque — estoque:read.
- POST /api/v1/estoque — estoque:create.
- PUT /api/v1/estoque/{id} — estoque:update.
- DELETE /api/v1/estoque/{id} — estoque:delete.
- Quantidade, mínimo e máximo aceitam até três casas decimais; valor unitário, duas. A data de cadastro, quando informada, deve ser válida no formato AAAA-MM-DD.
- O service bloqueia alteração direta de saldo quando há movimentos e bloqueia exclusão de produto referenciado por movimentações. Ajustes de saldo devem passar por /api/v1/acertos-estoque.
- Admin e Operador possuem CRUD de produtos no catálogo atual; capacidades de acerto são separadas.

### Paridade ainda pendente

A tela ainda não integra fotos, armazenamento externo, scanner por câmera/código de barras, impressão de etiquetas, checklist, relatórios por setor ou histórico de movimentações. A listagem da API não expõe filtros nem paginação. Não habilitar ações até integrar autenticação e definir o tratamento de arquivos, concorrência, auditoria e operações de exclusão.

## Acerto de Estoque

A interface Shadow inclui o formulário de entrada/saída e o histórico de movimentações. Tipo, produto, quantidade e motivo são obrigatórios. Quantidade aceita até três casas decimais e deve ser positiva. A data/hora é gerada pelo backend.

### API e integridade

- GET /api/v1/acertos-estoque — acertos_estoque:read.
- POST /api/v1/acertos-estoque — acertos_estoque:create.
- GET /api/v1/motivos-acerto-estoque — motivos_estoque:read (catálogo de motivos).
- Admin e Operador têm leitura e criação de movimentos.
- Entrada incrementa e saída decrementa saldo. Saída acima do saldo retorna HTTP 409.
- No PostgreSQL, saldo e histórico são gravados na mesma transação, com SELECT FOR UPDATE no produto.
- Não há rotas de edição ou exclusão. O service rejeita exclusão e orienta movimento compensatório.

A interface permanece bloqueada, sem rede ou dados fictícios, até integração da sessão Google/Bearer e API HTTPS isolada. Scanner, anexos, aprovação, filtros/paginação e auditoria explícita do movimento ainda precisam de evolução.

## Usuários e controle de acesso

A tela Shadow mantém o módulo bloqueado até a integração da sessão Google validada e da API HTTPS isolada. Não há formulário de senha local, redefinição de senha local ou cadastro público. A identidade é autenticada pelo Google; o e-mail verificado deve corresponder a um único cadastro interno Bravo e somente status Ativo autoriza acesso. Perfil e capacidades vêm do cadastro interno.

### API e salvaguardas observadas

- GET /api/v1/usuarios e GET /api/v1/usuarios/{id}: usuarios:read.
- POST /api/v1/usuarios: usuarios:create; cria cadastro comum como Operador/Ativo, sem aceitar perfil/status enviados pelo cliente.
- PUT /api/v1/usuarios/{id}: usuarios:update; altera somente nome, loja e cargo, preservando e-mail, perfil e status.
- POST /api/v1/usuarios/{id}/desativar: usuarios:deactivate; desativação lógica com auditoria na mesma transação PostgreSQL.
- DELETE /api/v1/usuarios/{id}: HTTP 410; exclusão física bloqueada.
- Operador não possui capacidades de usuários; administração é restrita ao perfil Admin.
- Desativação impede auto-desativação e o repositório impede desativar o último Admin ativo.

### Pendências

A interface ainda não está ligada à API. A alteração administrativa de perfil/status existe como método interno, mas não está exposta por rota; não criar tela que prometa essa ação. O cadastro cria Operador ativo, então provisionamento inicial de Admin e processo de aprovação de novas contas precisam permanecer controlados fora do auto-cadastro. Não habilitar operações antes da integração Google/Bearer.

## Integração transversal — cliente HTTP autenticado

Foi criado `frontend/js/bravo-api.js` como cliente comum para a futura integração das telas com a API Shadow. Ele exige URL HTTPS (HTTP somente em localhost), restringe caminhos a `/api/v1/`, obtém o Bearer dinamicamente da sessão Google em memória, usa `credentials: omit`, `cache: no-store`, `referrerPolicy: no-referrer` e `redirect: error`, e padroniza erros com status e `X-Request-ID`.

O cliente ainda não está importado pelo `index.html` nem usado pelas telas. Isso é intencional: ainda não existe uma URL HTTPS isolada da API nem allowlist CORS aprovada. A API FastAPI mantém CORS fechado e o backend inicia em memória por padrão; PostgreSQL só deve ser selecionado explicitamente no ambiente isolado.

### Bloqueios antes de conectar telas

1. Disponibilizar API em origem HTTPS separada e gratuita/aceita, sem publicar no domínio de produção.
2. Definir origem exata do preview Shadow e configurar CORS por allowlist, sem curinga.
3. Configurar `GOOGLE_CLIENT_ID` no backend e as origens autorizadas no Google Identity Services.
4. Provisionar ambiente PostgreSQL descartável Shadow e definir `BRAVO_STORAGE_BACKEND=postgres`; nunca usar memória como persistência operacional.
5. Integrar `google-auth.js` e `bravo-api.js` no bootstrap da interface; encerrar sessão, abortar requisições e limpar estado em logout/expiração.
6. Conectar módulos em etapas, verificando capacidade por rota e erros 401/403/409/422.
7. Confirmar auditoria, paginação, limites de upload e políticas de arquivos antes de liberar operações sensíveis.

## Preparação de container e isolamento de hospedagem

O `Dockerfile` foi endurecido para hospedagem Shadow: imagem Python 3.12 slim, usuário sem privilégios, frontend estático incluído e inicialização bloqueada a menos que `BRAVO_STORAGE_BACKEND=postgres`, `BRAVO_DATABASE_URL` e `GOOGLE_CLIENT_ID` estejam definidos. A porta usa `PORT` do provedor ou 8000. `.env.example` contém apenas placeholders e `.dockerignore` já exclui `.env`, diretórios Git e artefatos locais.

O Worker Cloudflare de prova agora está com `workers_dev=false`, origem CORS de placeholder não utilizável e validação de `azp` quando presente no ID token. Isso é apenas configuração de segurança; nenhum Worker foi publicado.

### Limitações que continuam impedindo hospedagem

- O FastAPI ainda não implementa middleware CORS/allowlist. Definir variável no ambiente não habilita CORS; permanece fechado.
- Não existe provedor/origem HTTPS isolada aprovado ou configurado.
- Não existe PostgreSQL Shadow provisionado; não preencher secrets com dados de produção.
- O Dockerfile é blueprint; não foi construído nem publicado.

## CORS por allowlist explícita

O FastAPI agora aceita a variável `BRAVO_CORS_ORIGINS` como lista separada por vírgulas de origens exatas. Sem valor, CORS continua fechado. Curinga `*`, credenciais/cookies, caminhos, query strings e origens HTTP públicas são rejeitados; HTTP é permitido somente em localhost para desenvolvimento. Métodos e cabeçalhos são limitados aos usados pela API e `ETag`/`X-Request-ID` são expostos.

O valor permanece vazio no `.env.example`; não foi inventada nem autorizada uma origem de preview. Ao definir hospedagem, preencher apenas com a origem HTTPS exata do frontend Shadow.

## Plano de homologação gratuita — Render + Supabase

Foi preparado `render.yaml` para um único serviço Docker no Render Free, servindo frontend e API na mesma origem HTTPS, com deploy automático desligado e branch `bravo-shadow`. O PostgreSQL fica em projeto Supabase Free isolado, sem usar Supabase Auth. O guia `docs/guia-homologacao-gratuita.md` descreve os passos manuais, secrets, OAuth, limitações e critérios de liberação.

Este material não cria contas ou recursos: nenhum deploy, banco, migration ou credencial foi criado/aplicado. A combinação gratuita é somente para homologação com dados sintéticos: Render adormece após inatividade e Supabase Free pode pausar por baixa atividade, não oferece backups automáticos e tem limite de 500 MB.

## Bootstrap Google — preparado e fechado por padrão

O arquivo `js/bravo-bootstrap.js` foi conectado ao shell como módulo ES. Ele coordena `google-auth.js` e `bravo-api.js`, mas **não ativa o login sem configuração explícita**.

Condições obrigatórias para inicializar:
- `window.BRAVO_SHADOW_CONFIG.enabled === true`;
- Client ID público Google válido;
- `apiBase` HTTPS (HTTP somente em localhost durante desenvolvimento);
- API na mesma origem da página, para manter a homologação sem CORS aberto.

Sem essas condições, o módulo mostra o motivo do bloqueio e não carrega o Google Identity Services, não chama a API e não tenta descobrir ou usar endereço de produção. Nenhum objeto de configuração habilitador foi adicionado ao HTML.

Após autenticação, a API continua sendo a autoridade para confirmar cadastro, e-mail verificado e status `Ativo`. O cliente HTTP recebe o token apenas em memória; nenhum token é persistido. O cliente permanece encapsulado no bootstrap e ainda não habilita operações dos módulos. A conexão funcional de cada módulo dependerá da homologação da API e das permissões correspondentes.

**Estado atual:** bootstrap conectado ao shell; login ainda desabilitado; API/host ainda não publicados; nenhuma chamada de negócio habilitada.


## Integração incremental — Dashboard

O shell encaminha os eventos `bravo:session-ready` e `bravo:session-ended`. O evento de sessão pronta contém um cliente HTTP com métodos de API e o perfil confirmado; não contém o ID token. O Dashboard usa esse cliente apenas para a rota de resumo protegida. A navegação invalida/cancela consultas pendentes, e o encerramento da sessão limpa a referência do cliente e repõe os indicadores indisponíveis.

O endpoint é agregado no backend e não devolve nomes, e-mails ou textos de documentos. A leitura não concede permissões: a autorização continua no servidor, por meio da capacidade `dashboard:read`.


## Financeiro — listagem autenticada somente leitura

A tela de Contas a Pagar / Receber consulta `GET /api/v1/financeiro` somente após receber o cliente da sessão Google autenticada. A rota exige a capacidade `financeiro:read`; os erros 401 e 403 são apresentados sem converter falhas em lista vazia bem-sucedida.

A tabela mostra tipo, identificador da conta do Plano de Contas, histórico e valor em BRL. O conteúdo recebido é inserido com `textContent`, sem interpretar históricos como HTML. Pesquisa textual e filtro por tipo são locais, aplicados somente à lista retornada pela API.

Inclusão, edição, exclusão e baixa permanecem desabilitadas. Não há chamadas POST, PUT ou DELETE no fluxo do módulo. A consulta é cancelada ao sair do módulo ou encerrar a sessão; respostas antigas não atualizam a tela após a navegação.

**Limites do contrato atual:** o título possui tipo, conta opcional, histórico e valor. Não há vencimento, competência, baixa, pagamento parcial, recorrência ou conciliação. A tabela não inventa esses campos nem calcula indicadores que o backend não fornece.

## Plano de Contas — consulta integrada

A tela do Plano de Contas utiliza o cliente HTTP entregue pelo evento de sessão Google e consulta exclusivamente `GET /api/v1/plano-contas`, protegido pela capacidade `plano_contas:read`. A resposta é validada antes da renderização; código, nome e tipo são inseridos como texto, sem interpretar conteúdo recebido como HTML. Pesquisa por código/nome e filtro por Receita/Despesa atuam localmente sobre a lista autorizada.

Ao encerrar a sessão, a lista em memória é limpa e requisições pendentes são canceladas. A navegação para outro módulo também invalida a consulta anterior. Cadastro, edição e exclusão continuam desabilitados, embora existam rotas correspondentes no backend. Nenhum dado fictício é apresentado.

A integração está preparada no código da branch Shadow, mas depende da API HTTPS isolada, da configuração explícita do bootstrap Google e da concessão de `plano_contas:read`. Não houve publicação nem alteração na aplicação original.

### Relacionamento entre Financeiro e Plano de Contas

Na listagem financeira, a interface consulta também `GET /api/v1/plano-contas` para resolver `planoContaId` em código e nome da conta. Essa consulta auxiliar usa a mesma sessão autenticada e sua própria autorização `plano_contas:read`. Se a permissão ou a consulta auxiliar não estiver disponível, a listagem de títulos continua funcionando e exibe o identificador interno como alternativa; não transforma uma falha auxiliar em falha do Financeiro.

A pesquisa financeira considera histórico, tipo, identificador e nome/código resolvido. Os dados auxiliares ficam apenas em memória e são descartados ao encerrar a sessão. Ambas as consultas são canceladas quando a tela deixa de ser atual; não há gravação nem alteração de vínculos.

## Contas Bancárias — consulta autenticada somente leitura

A tela consulta exclusivamente `GET /api/v1/contas-bancarias` após receber a sessão Google autenticada. O endpoint exige `contas_bancarias:read`. A resposta é validada quanto a identificador, nome do banco e saldo numérico antes de renderizar a tabela; valores são formatados em BRL e conteúdo textual é inserido via `textContent`.

O saldo é apresentado como **saldo informado**, conforme o contrato atual, e não como saldo conciliado, extrato ou cálculo de movimentações. A tela não inventa agência, número de conta, instituição por código ou datas de saldo. Cadastro, edição e exclusão permanecem bloqueados; a API possui rotas de gravação, mas não são chamadas pela interface.

A consulta é cancelada ao sair do módulo e ao encerrar a sessão. A lista em memória é limpa no logout. O módulo depende da API HTTPS isolada, do bootstrap Google habilitado explicitamente e da permissão `contas_bancarias:read`; nenhuma publicação foi realizada.

## Formas Monetárias — consulta autenticada somente leitura

A tela consulta exclusivamente `GET /api/v1/formas-monetarias` com a sessão Google autenticada e a capacidade `formas_monetarias:read`. A resposta é validada quanto a identificador, nome e percentual de multa (entre 0 e 100) antes de renderizar. Nome e valores são inseridos como texto; o percentual é formatado com duas casas decimais.

Cadastro, edição e exclusão permanecem desabilitados e não são chamados pela interface. A consulta é cancelada ao navegar para outro módulo; a lista em memória é descartada no encerramento da sessão. O módulo não presume que a multa seja aplicada automaticamente a títulos: apenas exibe o percentual persistido no contrato atual.


## Relatórios & DRE — consulta gerencial integrada

A tela consulta exclusivamente `GET /api/v1/relatorios/dre` após receber o cliente HTTP da sessão Google validada. A rota exige `relatorios:read` e agrega os serviços existentes de Financeiro e Plano de Contas, sem duplicar armazenamento e sem executar gravações.

O relatório apresenta quantidade e valor total de títulos Receber/Pagar, diferença aritmética explicitamente identificada como diferença entre títulos e agrupamento por conta vinculada. A classificação principal segue o tipo do título, preservando o comportamento histórico mesmo quando o tipo cadastrado na conta divergir. Títulos sem conta (ou com referência não resolvida) continuam nos totais gerais e são informados separadamente, sem aparecer nas linhas agrupadas. Valores são agregados com Decimal no backend.

**Limites deliberados:** o contrato financeiro não possui datas de competência, vencimento, pagamento/recebimento ou status de liquidação. Portanto, a consulta inclui todos os títulos cadastrados, sem filtro temporal ou de situação. Não oferece DRE contábil por competência, realizado versus previsto, inadimplência, conciliação bancária ou exportação PDF/Excel. A diferença entre Receber e Pagar não é saldo em caixa nem saldo bancário. A interface valida a resposta, usa `textContent`, cancela requisições obsoletas e limpa os dados em memória no encerramento da sessão.

A implementação está na branch Shadow, mas não foi ativada em hospedagem nem conectada a dados de produção. Depende da API HTTPS isolada, do bootstrap Google explicitamente habilitado e da capacidade `relatorios:read`.


## Autenticação Google e autorização central

A cadeia de autenticação, vínculo com cadastro ativo e cobertura de capacidades dos routers está registrada em [Auditoria de autenticação Google e autorização de rotas](../docs/auditoria-autenticacao-google-autorizacao-rotas.md). A autenticação valida o ID token no backend e resolve o perfil exclusivamente pelo usuário interno ativo. A interface não concede permissões; cada endpoint de negócio aplica sua capacidade no servidor. O bootstrap segue opt-in e não foi ativado nesta revisão.


### Capacidades efetivas na sessão

A resposta autenticada de `GET /api/v1/auth/me` inclui `capabilities`, calculada no backend a partir do perfil Bravo ativo e da matriz explícita `ROLE_CAPABILITIES`. O módulo `google-auth.js` exige que a propriedade seja uma lista válida, sem valores vazios ou duplicados, e a congela na sessão entregue aos módulos. Essa lista pode orientar a apresentação de controles, mas não autoriza operações: cada endpoint continua validando sua capacidade no servidor. Ausência ou formato inválido da lista impede a abertura da sessão; nenhuma permissão é presumida no navegador.
