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
