# Auditoria de autenticação Google e autorização de rotas — Bravo Shadow

Data da revisão: 2026-11-27  
Escopo: branch `bravo-shadow`; revisão estática dos arquivos de autenticação, autorização, bootstrap e routers registrados em `backend/app/main.py`.

## Resultado

A cadeia de autenticação e autorização já está implementada no backend e conectada ao bootstrap do frontend. A revisão dos routers registrados confirmou que as rotas de negócio analisadas exigem dependência de identidade Google e capacidade específica; a rota `/api/v1/auth/me` exige identidade validada; somente `/api/v1/health` permanece pública para health check. Não foi necessário introduzir permissões presumidas ou alterar a tela de login nesta etapa.

## Cadeia de confiança

1. O Google Identity Services entrega um ID token ao navegador.
2. O frontend envia o token como Bearer para `GET /api/v1/auth/me`; só após resposta válida emite `bravo:session-ready`.
3. O backend valida assinatura, emissor, audiência configurada em `GOOGLE_CLIENT_ID` e expiração usando `google-auth`.
4. O backend exige `sub`, e-mail textual e `email_verified is True`; normaliza o e-mail para minúsculas e espaços externos.
5. O cadastro interno é pesquisado por e-mail. Exatamente um usuário com status `Ativo` é obrigatório; zero, duplicidade ou inatividade negam acesso.
6. Perfil e status vêm do cadastro Bravo, não de claims de perfil do Google. A autorização é resolvida no servidor por capacidade. O endpoint `/api/v1/auth/me` também devolve a lista explícita de capacidades efetivas do perfil, calculada pela mesma matriz `ROLE_CAPABILITIES`; o frontend exige essa lista, valida tipo/duplicidade e a mantém imutável na sessão.
7. Cada dependência de capacidade chama primeiro `get_current_principal`, depois aplica a matriz de perfil. Falha de capacidade resulta em 403; falha/ausência de token resulta em 401; configuração ausente do servidor resulta em 503.

## Matriz de perfil observada

- **Admin:** todas as capacidades explicitamente listadas em `CAPABILITIES`.
- **Operador:** rotina operacional e leitura de cadastros/configurações; sem administração de usuários nem alteração de configurações. A matriz concede explicitamente `relatorios:read`, que também protege os relatórios de Compras x Consumo.
- Perfil desconhecido, principal inválido ou conta diferente de `Ativo`: nenhuma capacidade.

A autorização não depende de botões ocultos na interface: as rotas são protegidas no servidor. A lista de capacidades enviada ao navegador serve para orientar a apresentação dos controles, nunca substitui a checagem da API. O módulo de usuários também não permite exclusão física: o DELETE responde 410 e a desativação lógica tem capacidade própria e auditoria.

## Cobertura das rotas registradas

| Área / prefixo | Proteção observada |
|---|---|
| `/api/v1/auth/me` | ID token Google válido e vínculo com usuário ativo |
| `/api/v1/dashboard` | `dashboard:read` |
| `/api/v1/compras-consumo` | `relatorios:read` (inclui exportação CSV) |
| `/api/v1/plano-contas` | `plano_contas:read/create/update/delete` |
| `/api/v1/relatorios` | `relatorios:read` |
| `/api/v1/financeiro` | `financeiro:read/create/update/delete` |
| `/api/v1/formas-monetarias` | `formas_monetarias:read/create/update/delete` |
| `/api/v1/contas-bancarias` | `contas_bancarias:read/create/update/delete` |
| `/api/v1/fornecedores` | `fornecedores:read/create/update/delete` |
| `/api/v1/empregados` | `empregados:read/create/update/delete` |
| `/api/v1/condominio` | `condominio:read/update` |
| `/api/v1/conselheiros` | `conselheiros:read/create/update/delete` |
| `/api/v1/moradores` | `moradores:read/create/update/delete/import` |
| `/api/v1/categorias` | `categorias:read/create/delete` |
| `/api/v1/motivos-acerto-estoque` | `motivos_estoque:read/create/delete` |
| `/api/v1/estoque` | `estoque:read/create/update/delete` |
| `/api/v1/acertos-estoque` | `acertos_estoque:read/create` |
| `/api/v1/documentos` | `documentos:read/create/update/delete` |
| `/api/v1/usuarios` | `usuarios:read/create/update/delete/deactivate`; DELETE físico bloqueado |
| `/api/v1/configuracoes` | `configuracoes:read/update` |
| `/api/v1/health` | Pública; health check sem dados de negócio |

## Proteções do navegador

- Bootstrap só inicia com `BRAVO_SHADOW_CONFIG.enabled === true`, Client ID válido e API HTTPS na mesma origem.
- A API não é descoberta automaticamente e o bootstrap não aponta para produção.
- O ID token permanece em memória; não é persistido em localStorage, sessionStorage ou cookies pelo módulo de autenticação.
- O cliente HTTP envia Bearer, usa `cache: no-store`, `credentials: omit`, `referrerPolicy: no-referrer` e rejeita redirects.
- O evento `bravo:session-ready` encaminha cliente e identidade confirmada, não o token. `bravo:session-ended` é disparado no logout, erro de autenticação e encerramento da página.

## Limites e próximos controles

- A revisão foi estática; não houve execução de testes, chamadas HTTP reais, inspeção de navegador, publicação ou conexão com banco nesta etapa.
- A autenticação não está ativada no ambiente publicado: o bootstrap continua opt-in e sem configuração habilitadora. Não ativar até API HTTPS isolada, OAuth autorizado para a origem de homologação e permissões de conta revisadas.
- A autorização de cada endpoint deve continuar sendo auditada quando novas rotas forem adicionadas. Toda nova rota de negócio deve declarar uma capacidade registrada em `CAPABILITIES` e incluída somente nos perfis aprovados.
- A matriz Admin/Operador é a matriz já registrada no código; qualquer mudança de permissões exige decisão explícita do responsável e revisão separada.

## Evidência consultada

- `backend/app/core/authentication.py`
- `backend/app/core/authorization.py` (`capabilities_for` deriva a lista efetiva do perfil)
- `backend/app/modules/auth/router.py` (inclui `capabilities` na resposta de `/me`)
- `frontend/js/google-auth.js` (valida e congela a lista recebida)
- `backend/app/modules/auth/router.py`
- `frontend/js/google-auth.js`
- `frontend/js/bravo-api.js`
- `frontend/js/bravo-bootstrap.js`
- Routers registrados em `backend/app/main.py`

Esta auditoria não altera o login nem a aplicação original. Toda a revisão e documentação permanecem na branch `bravo-shadow`.
