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

O módulo **Formas Monetárias** já utiliza a API relativa `/api/v1/formas-monetarias` para listar, cadastrar, editar e excluir registros. A interface apresenta estados de carregamento e erro, valida o nome e a multa (0–100%) e escapa os valores exibidos.

O backend deste módulo ainda utiliza armazenamento em memória. Os registros são exclusivos do processo do ambiente sombra e são perdidos quando ele reinicia. Isso não é persistência definitiva nem integração com o banco de produção.

Os demais módulos continuam identificados como estrutura visual até que seus contratos e fluxos sejam conectados individualmente.

## Dashboard — integração visual segura

A tela inicial apresenta o contrato do resumo protegido `GET /api/v1/dashboard/resumo`, mas mantém os indicadores indisponíveis até a integração da sessão Google no navegador. A API exige um ID token Google no cabeçalho Bearer e a capacidade `dashboard:read`; a matriz de perfis continua fechada por padrão.

A interface não inventa valores, não interpreta falha de autenticação como zero e não tenta armazenar tokens em `localStorage` ou em variáveis globais. O próximo passo é conectar o bootstrap de sessão à URL HTTPS da API e só então renderizar o resumo após resposta autorizada.

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
