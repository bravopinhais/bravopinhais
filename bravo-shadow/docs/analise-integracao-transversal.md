# Análise de integração transversal — Bravo Shadow

Data: 27/11/2026

## Estado verificado

### Frontend

- `frontend/js/google-auth.js` implementa inicialização Google Identity Services, recebe a credencial, chama `GET /api/v1/auth/me`, mantém ID token somente em memória e fornece cabeçalho Bearer/signOut/dispose.
- `frontend/index.html` não importa `google-auth.js`, não apresenta botão Google e não inicializa sessão.
- As telas de módulos permanecem deliberadamente bloqueadas, sem requisições autenticadas nem dados fictícios.
- `frontend/js/bravo-api.js` foi criado como cliente HTTP compartilhado, mas ainda não está integrado ao HTML.

### Backend

- `GET /api/v1/auth/me` valida identidade por `get_current_principal` e devolve subject, e-mail, perfil e status internos.
- `verify_google_id_token` usa google-auth com `GOOGLE_CLIENT_ID` configurado no servidor; o vínculo é feito por e-mail verificado e único, com status Ativo.
- `main.py` inclui os routers dos módulos e mantém CORS fechado até definição da allowlist.
- `create_app()` seleciona `memory` por padrão; PostgreSQL exige seleção explícita e conexão configurada.
- A API serve o frontend estático se a pasta existir, mas isso não constitui hospedagem HTTPS isolada nem publicação do preview.

## Cliente HTTP compartilhado

`frontend/js/bravo-api.js` implementa `createBravoApiClient({ apiBase, getAuthorizationHeader })` e métodos GET/POST/PUT/PATCH/DELETE. A URL base deve ser HTTPS, exceto HTTP em localhost. Caminhos são restritos a `/api/v1/`. O Bearer é obtido dinamicamente da sessão; não há armazenamento de token. Requisições usam `credentials: omit`, `cache: no-store`, `referrerPolicy: no-referrer` e `redirect: error`. Erros incluem status HTTP e `X-Request-ID` quando disponível.

O cliente não foi conectado às telas, pois a API e o preview ainda não possuem origens isoladas aprovadas. Não inventar uma URL ou liberar chamadas para a produção.

## Bloqueios de ambiente

1. Escolher e disponibilizar uma origem HTTPS independente para o frontend Shadow, sem usar o domínio de produção.
2. Disponibilizar uma API HTTPS independente, com política de custo compatível com a decisão do usuário.
3. Configurar CORS somente para a origem exata do frontend Shadow; manter curinga proibido.
4. Configurar `GOOGLE_CLIENT_ID` no backend e a mesma client ID pública/origens autorizadas no Google Identity Services.
5. Configurar PostgreSQL descartável Shadow e selecionar explicitamente `BRAVO_STORAGE_BACKEND=postgres`; nunca usar memória como persistência operacional.
6. Confirmar health, autenticação e CORS no ambiente isolado antes de conectar qualquer tela.

## Sequência de integração proposta

1. Resolver frontend/API/origens e variáveis de ambiente sem deploy na produção.
2. Integrar bootstrap Google no HTML: estados não autenticado, autenticando, autenticado e erro; logout deve descartar token e abortar operações pendentes.
3. Instanciar cliente HTTP apenas após confirmação da sessão Google e configuração HTTPS.
4. Criar camada de estado de sessão e autorização; a UI pode ocultar ações, mas o backend permanece a autoridade final.
5. Conectar primeiro leituras de baixo risco; depois operações de cadastro; por último ações sensíveis, arquivos e importações.
6. Para cada módulo, respeitar capacidades, versionamento/ETag, conflitos, paginação e auditoria disponíveis.
7. Arquivos: definir tamanho máximo, tipo permitido, antivírus/validação, armazenamento privado, URLs assinadas e política de retenção antes de habilitar upload/download.
8. Sincronização/offline: só projetar fila e reconciliação depois de definir versionamento, idempotência, resolução de conflito e política de dados locais.

## Lacunas transversais adicionais

- Não há bootstrap de sessão no HTML; por isso nenhuma tela pode ser ativada com segurança ainda.
- CORS está intencionalmente fechado.
- Ambiente PostgreSQL ainda não está provisionado nem selecionado em hospedagem.
- Não existe URL de preview independente confirmada.
- O fluxo de recuperação/revalidação e expiração de sessão precisa ser conectado à UI.
- Persistência offline, sincronização, fila de pendências e reconciliação não estão integradas.
- Não assumir que auditoria esteja presente em todas as operações CRUD; verificar rota/repositório por módulo.
- Documentos ainda armazenam Gzip/Base64 no banco; armazenamento externo privado e URLs assinadas não estão implementados.

## Limites desta etapa

Adicionado apenas o cliente HTTP comum e documentação de integração. Nenhuma tela foi conectada, nenhum endpoint foi chamado, nenhum teste executado, nenhuma variável/secret configurada, nenhum banco conectado, nenhum deploy/publicação ou alteração em `main`/produção.