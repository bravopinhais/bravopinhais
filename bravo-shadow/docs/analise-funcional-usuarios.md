# Análise funcional — Usuários e controle de acesso

Data: 27/11/2026

## 1. Legado

A tela antiga apresenta usuário/login, nome, e-mail, loja/unidade, cargo, ações de senha, edição e exclusão. O modal contém login, nome, e-mail, loja, cargo e senha temporária; há fluxo local de redefinição de senha. Esses fluxos locais não serão portados para o Bravo Shadow.

## 2. Regra de identidade do Shadow

Google autentica a identidade. O backend valida ID token, issuer, audience, expiração, subject e e-mail verificado. O e-mail deve corresponder a exatamente um cadastro interno Bravo. Apenas status Ativo autoriza acesso. Perfil e capacidades são obtidos do cadastro interno. Não há senha local, reset local nem auto-registro.

## 3. Contratos observados

- GET /api/v1/usuarios e GET /api/v1/usuarios/{id}: usuarios:read.
- POST /api/v1/usuarios: usuarios:create; recebe e-mail, nome, loja e cargo; força perfil Operador e status Ativo.
- PUT /api/v1/usuarios/{id}: usuarios:update; altera somente nome, loja e cargo; e-mail, perfil e status permanecem preservados.
- DELETE /api/v1/usuarios/{id}: HTTP 410; exclusão física bloqueada.
- POST /api/v1/usuarios/{id}/desativar: usuarios:deactivate; desativa logicamente e registra auditoria na mesma transação PostgreSQL.

Os schemas recusam campos extras, normalizam e-mail e validam campos cadastrais. A resolução por e-mail usa busca indexada no adapter PostgreSQL e identifica duplicidades.

## 4. Permissões e salvaguardas

Capacidades de administração de usuários pertencem ao perfil Admin; Operador não recebe acesso ao módulo. A desativação exige ator Ativo, impede desativar a própria conta e o adapter impede desativar o último Admin ativo. A alteração de perfil/status existe como método interno protegido para Admin e auditado, mas não está exposta por rota.

## 5. Interface Shadow

A função usuariosView() é um painel de pré-requisitos, não um CRUD ativo. Informa que sessão Google, consulta autenticada e permissões estão pendentes. Não chama API e não exibe dados fictícios. Deve continuar assim até autenticação Google e API HTTPS isolada estarem integradas.

## 6. Pendências e decisões

1. Integrar o token Google validado no navegador e chamadas Bearer à API HTTPS isolada.
2. Definir processo controlado de provisionamento do primeiro Admin; o cadastro comum cria apenas Operador Ativo.
3. Definir aprovação/validação de novas contas antes de liberar o POST de cadastro a administradores.
4. Se necessário, projetar rota administrativa para perfil/status com autorização, trilha de auditoria e proteção do último Admin; não presumir que o método interno já esteja disponível via API.
5. Construir interface administrativa somente depois das decisões e integração.

## 7. Limites

Comparação estática e documentação. Nenhum teste executado, banco conectado, SQL aplicado, deploy/publicação ou alteração em main/dados de produção.