# Autenticação Google — Bravo Shadow

## Implementado nesta etapa

- Validação de ID token Google no servidor com `google-auth`.
- A biblioteca verifica assinatura, emissor, audiência e expiração.
- A audiência é o `GOOGLE_CLIENT_ID` configurado no servidor.
- Exigência de `sub`, e-mail e `email_verified=true`.
- Vínculo do e-mail verificado ao cadastro interno Bravo, normalizado sem distinção de caixa.
- Usuário ausente, duplicado ou inativo é negado.
- Perfil e status vêm exclusivamente do cadastro interno, nunca do browser.
- Dependency reutilizável `get_current_principal`.

## Ainda não ativado

A dependency ainda não foi aplicada aos routers. As rotas atuais permanecem sem autenticação até a etapa de integração e teste por módulo. Não usar a API sombra com dados reais ou expô-la publicamente neste estado.

## Configuração futura

Definir `GOOGLE_CLIENT_ID` com o Client ID OAuth do projeto Google correto no ambiente servidor. Não inserir segredo/token no repositório, frontend ou arquivo versionado. O Client ID não é um segredo, mas deve corresponder exatamente à audiência emitida pelo login do frontend.

## Segurança e limites

- O backend nunca confia em e-mail, perfil ou status enviados em JSON.
- Um ID token válido prova a identidade Google, mas o acesso ao Bravo depende também do cadastro interno ativo.
- A associação inicial é pelo e-mail Google verificado. Caso o Bravo precise suportar troca de e-mail ou múltiplos provedores, deverá ser criado vínculo imutável por `sub` após decisão funcional.
- Não há refresh token, sessão própria, logout remoto ou autorização aplicada aos endpoints nesta entrega.
- `/api/v1/health` permanece público.
- Antes de integrar as rotas, testar a dependency com token real de homologação, Client ID correto e matriz de capacidades aprovada.
