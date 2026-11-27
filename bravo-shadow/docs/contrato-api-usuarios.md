# Contrato da API de usuários — Bravo Shadow

**Status:** rotas implementadas na API sombra; nenhuma capability de usuário está liberada para os perfis atuais; sessão Google ainda não está integrada ao frontend.

## Princípios

- A identidade de autenticação vem de um ID token Google validado no servidor.
- O e-mail Google precisa estar verificado e corresponder a exatamente um cadastro interno ativo.
- O e-mail é normalizado com remoção de espaços e conversão para minúsculas; cadastros duplicados são rejeitados.
- O CRUD cadastral não pode atribuir nem alterar perfil, status ou e-mail.
- Perfil e status são dados administrativos e não devem ser expostos sem autorização específica e auditoria transacional.

## Rotas

| Método e rota | Payload | Comportamento |
|---|---|---|
| GET `/api/v1/usuarios` | — | Lista usuários; exige `usuarios:read`. |
| GET `/api/v1/usuarios/{id}` | — | Consulta um usuário; exige `usuarios:read`. |
| POST `/api/v1/usuarios` | `email, nome, loja?, cargo` | Cria como `Operador` e `Ativo`; exige `usuarios:create`. |
| PUT `/api/v1/usuarios/{id}` | Um ou mais entre `nome, loja, cargo` | Atualiza somente dados cadastrais e preserva e-mail, perfil e status; exige `usuarios:update`. |
| DELETE `/api/v1/usuarios/{id}` | — | Retorna `410 Gone`; exclusão física pela API está bloqueada. |
| POST `/api/v1/usuarios/{id}/desativar` | — | Desativa logicamente, preserva o registro e grava auditoria na mesma transação; exige `usuarios:deactivate`. |

Os schemas rejeitam campos extras. Portanto, o POST não aceita perfil/status fornecidos pelo cliente e o PUT não aceita troca de e-mail, perfil ou status. A unicidade do e-mail é verificada sem diferenciar maiúsculas/minúsculas no serviço em memória; o rascunho SQL também prevê índice único sobre `lower(btrim(email))`.

## Administração de perfil e status

O schema `UsuarioAdministracaoInput` e a operação de serviço transacional existem, mas não há rota pública para essa alteração. Não habilitar essa operação sem:
- capability administrativa aprovada explicitamente;
- persistência e auditoria na mesma transação;
- autenticação Google integrada ao cliente;
- proteção contra autoalteração e remoção do último Admin ativo;
- testes HTTP e transacionais correspondentes.

## Autorização atual

As matrizes de capabilities para `Admin` e `Operador` permanecem vazias. As rotas continuam negando acesso até aprovação explícita da matriz. A existência de uma rota ou de um serviço não significa que o perfil tenha permissão para executá-los.

## Estado do frontend

O módulo Gestão de Usuários do frontend sombra permanece como placeholder visual. O `apiRequest()` ainda não injeta o ID token Bearer Google. Assim, as rotas não estão integradas à interface e os indicadores/ações de usuários não devem ser apresentados como operacionais.

## Persistência e migração

O rascunho `docs/sql-piloto-financeiro.sql` contém o índice único case-insensitive para e-mail. O arquivo é apenas proposta de DDL: não foi aplicado a banco, não cria concessões de acesso nem policies RLS. Nenhum dado real foi importado.
