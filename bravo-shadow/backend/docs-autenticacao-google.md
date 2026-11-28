# Autenticação Google — Bravo Shadow

## Estado implementado na branch bravo-shadow

- O navegador obtém um Google ID token por meio do Google Identity Services.
- O backend valida o ID token no servidor com `google-auth`, usando `GOOGLE_CLIENT_ID` como audiência.
- A validação verifica assinatura, emissor, audiência e expiração.
- O backend exige `sub`, e-mail textual e `email_verified=true`.
- O e-mail é normalizado e vinculado a exatamente um cadastro interno.
- Cadastro inexistente, duplicado ou com status diferente de `Ativo` é negado.
- Perfil, status e capacidades são obtidos do cadastro interno e da matriz central; nunca são aceitos do browser.
- `GET /api/v1/auth/me` retorna a identidade validada e as capacidades efetivas.
- As rotas de negócio possuem dependência de identidade Google e barreira de capacidade. A cobertura é verificada automaticamente por `test_route_authentication_coverage.py`.
- `GET /api/v1/health` é a única rota pública de sistema; `GET /api/v1/auth/me` é o endpoint autenticado de identidade.

## Configuração necessária no servidor

Definir `GOOGLE_CLIENT_ID` no ambiente do backend com o Client ID OAuth correspondente ao projeto Google configurado no frontend. O Client ID é identificador público; nenhum Client Secret deve ser colocado no frontend ou versionado no repositório.

A API deve ser publicada somente em HTTPS, com `BRAVO_CORS_ORIGINS` limitado às origens exatas aprovadas. O backend deve usar armazenamento PostgreSQL explicitamente configurado para homologação persistente; não usar fallback silencioso para memória.

## Limite atual do vínculo de identidade

A associação inicial é feita pelo e-mail Google verificado. O claim `sub` é validado e usado como identificador do principal/auditoria, mas ainda não está persistido como vínculo imutável no cadastro Bravo.

A evolução para vínculo persistente por `sub` está descrita separadamente em `docs/plano-vinculo-identidade-google.md`. Não preencher esse vínculo automaticamente por coincidência de e-mail. Até aprovação e implementação do processo administrativo, alteração de e-mail e recuperação de conta exigem tratamento controlado.

## Limites de implantação

- A autenticação e autorização do backend não significam que a API esteja publicada ou acessível pelo GitHub Pages.
- O GitHub Pages hospeda somente os arquivos estáticos; não executa FastAPI.
- A prova isolada em `deploy/cloudflare-worker/` valida o caminho de identidade no runtime Worker, mas ainda não substitui a API completa nem seu armazenamento.
- Não conectar o sistema original, importar dados reais, executar dual-write ou fazer cutover nesta etapa.
- Não reintroduzir senha local, cadastro automático ou credenciais no navegador.

## Homologação pendente

Antes de liberar uso funcional, concluir:
1. Hospedagem HTTPS gratuita e compatível para a API completa, sem ativar recursos pagos.
2. Integração real entre frontend, API e PostgreSQL isolado de homologação.
3. Verificação de identidade, capacidades e auditoria em todas as rotas.
4. Validação do papel efetivo do usuário PostgreSQL, RLS, políticas e separação entre credenciais de runtime e migração.
5. Homologação integrada dos módulos e autorização expressa antes de qualquer importação real.

A execução automatizada dos testes de código não equivale a homologação operacional nem autoriza publicação ou importação.
