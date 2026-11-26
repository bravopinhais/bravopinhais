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
- Não há refresh token, sessão própria ou logout remoto nesta entrega.
- Autorização por capacidades está aplicada aos módulos Usuários e Financeiro na branch sombra; os outros 13 módulos de negócio continuam sem proteção.
- `/api/v1/health` permanece público.
- Antes de integrar as rotas, testar a dependency com token real de homologação, Client ID correto e matriz de capacidades aprovada.


## Endpoint de identidade da sessão

Foi adicionado `GET /api/v1/auth/me`, protegido por `get_current_principal`. Ele retorna apenas `subject`, `email`, `profile` e `status` depois da validação do token e da consulta ao cadastro interno.

Este endpoint permite validar o fluxo de identidade antes de proteger os módulos. As rotas de Usuários e Financeiro também exigem identidade e capacidade. Os outros 13 módulos de negócio ainda não estão protegidos e não devem ser expostos publicamente.

Testes automatizados escritos para: ausência de Bearer token (401), identidade Google válida vinculada a usuário ativo (200), e-mail sem cadastro (403) e token inválido (401). A execução ainda depende de CI ou ambiente Python configurado.
