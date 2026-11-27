# Contrato da API de usuários — Bravo Shadow

**Status: implementado na API sombra; sem capacidades liberadas e sem integração de sessão no frontend.**

## Princípio de separação

O CRUD cadastral não pode atribuir ou modificar privilégios. Perfil e status são dados administrativos e devem passar exclusivamente por uma operação administrativa separada, com autenticação Google, autorização específica e auditoria transacional.

## Rotas atuais

| Método e rota | Payload | Efeito |
|---|---|---|
| GET `/api/v1/usuarios` | — | Lista usuários; exige `usuarios:read` |
| GET `/api/v1/usuarios/{id}` | — | Consulta usuário; exige `usuarios:read` |
| POST `/api/v1/usuarios` | `email, nome, loja?, cargo` | Cria sempre como `Operador` e `Ativo`; exige `usuarios:create` |
| PUT `/api/v1/usuarios/{id}` | Um ou mais entre `nome, loja, cargo` | Atualiza somente cadastro; preserva e-mail, perfil e status; exige `usuarios:update` |
| DELETE `/api/v1/usuarios/{id}` | — | Ainda é exclusão física legada; exige `usuarios:delete`; matriz de permissões continua fechada |

Os schemas cadastrais rejeitam campos extras. Assim, tentativa de enviar `perfil`, `status` ou substituir o `email` no PUT não faz parte do contrato e deve retornar erro de validação. No POST, perfil/status não são aceitos e o servidor define os valores iniciais seguros.

## Administração de perfil/status

O schema `UsuarioAdministracaoInput` e o serviço transacional de alteração já existem. A operação ainda não possui rota pública. Antes de expô-la, são necessários:
- capability administrativa dedicada, aprovada explicitamente;
- injeção segura do sink PostgreSQL de auditoria;
- autenticação Google ligada ao frontend e validação de sessão;
- proteção contra autoalteração e último Admin ativo;
- teste HTTP de autorização e de atomicidade.

## Compatibilidade do frontend

O módulo Gestão de Usuários do frontend sombra ainda é apenas um placeholder visual. Não há formulário ativo chamando estas rotas. O `apiRequest()` ainda não injeta o ID token Bearer Google. Portanto, a mudança do contrato do PUT não rompe uma tela de usuários já integrada no Shadow; a interface deve ser implementada com os campos acima e sem controles de perfil/status até a etapa administrativa.

## Desativação lógica — não implementada ainda

O DELETE ainda chama exclusão física. A política proposta em `politica-desativacao-usuarios.md` define a direção futura, mas não muda o comportamento atual. Não converter DELETE silenciosamente sem alinhar o contrato e a experiência da interface. A próxima implementação deverá preferir ação explícita de desativar, preservando histórico e bloqueando login de usuários inativos.
