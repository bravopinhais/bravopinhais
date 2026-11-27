# Política de desativação de usuários — Bravo Shadow

**Status: implementada na API sombra; capacidade ainda não concedida a nenhum perfil.**

## Estado implementado

- O cadastro mantém os estados `Ativo` e `Inativo`.
- A autenticação Google só resolve usuário ativo; usuário inativo não recebe principal autenticado.
- A rota explícita `POST /api/v1/usuarios/{id}/desativar` executa desativação lógica.
- O registro permanece na tabela; somente o status, `updated_at` e `version` são atualizados.
- O evento `usuarios:desativar` é inserido pela mesma conexão e transação da mudança.
- A operação bloqueia auto-desativação e impede desativar o último Admin ativo.
- Falha ao inserir auditoria reverte a mudança de status.
- A capacidade `usuarios:deactivate` está declarada, mas Admin e Operador continuam sem capacidades atribuídas. O endpoint não está liberado.
- O DELETE legado responde 410 Gone e não realiza exclusão física.
- No armazenamento em memória, a operação auditada falha fechado com 503.

## Regras operacionais

1. Desligamento de acesso deve usar desativação lógica: manter o cadastro e alterar `status = 'Inativo'`.
2. Preservar e-mail Google, identidade, referências e histórico.
3. Nunca permitir que o último Admin ativo seja desativado.
4. Impedir auto-desativação.
5. Não criar senha local nem credencial paralela ao Google.
6. Exclusão física fica fora da API comum e exige procedimento excepcional de retenção/privacidade, com aprovação explícita.

## Limites e pré-requisitos para liberar

- A matriz de permissões Admin/Operador precisa ser aprovada antes de conceder `usuarios:deactivate`.
- O ambiente PostgreSQL precisa ter schema e tabela de auditoria preparados e grants mínimos revisados. Nenhuma migration, role, policy ou grant foi aplicado por esta implementação.
- A interface ainda precisa receber a sessão Google validada e apresentar ação explícita de desativação com confirmação.
- Os testes de integração usam PostgreSQL descartável e DDL de teste; não demonstram que um banco de produção esteja configurado.
- O endpoint não deve ser liberado enquanto a API não estiver usando a persistência PostgreSQL e o sink de auditoria configurado.

## Não fazer nesta etapa

- Não habilitar capacidades de perfil sem aprovação explícita.
- Não aplicar SQL, migration, roles, policies ou grants.
- Não conectar banco de produção.
- Não importar, apagar ou modificar dados reais.
- Não redesenhar a tela de login nem criar autenticação por senha.

## Critério de aceite

Uma desativação autorizada deve preservar o registro, bloquear autenticação futura do usuário inativo, manter pelo menos um Admin ativo e confirmar/reverter status e evento de auditoria como uma única transação.
