# Política proposta de desativação de usuários — Bravo Shadow

**Status: proposta técnica; não aplicada e não exposta por rota.**

## Estado observado no código

- O cadastro possui `status` com valores `Ativo` e `Inativo`.
- A resolução de identidade Google exige usuário único por e-mail e status ativo; usuário inativo não deve receber principal autenticado.
- O endpoint legado `DELETE /api/v1/usuarios/{item_id}` ainda chama `UsuariosService.delete()`, que executa exclusão física no repositório.
- O método transacional `update_administrative_state` já altera perfil/status e registra evento de auditoria na mesma transação PostgreSQL, com proteção do último Admin ativo.
- Essa operação administrativa ainda não está ligada a rota, e o `PostgresAuditSink` ainda não foi injetado na aplicação.
- A matriz de capacidades continua fechada; portanto, a rota DELETE existente não é autorizada para Admin ou Operador neste momento.

## Decisão técnica recomendada

1. Tratar desligamento de acesso como **desativação lógica**: manter o registro e alterar `status = 'Inativo'`.
2. Registrar a ação em `audit_events` na mesma transação que altera o status.
3. Impedir desativar/rebaixar o último Admin ativo; a proteção transacional existente deve ser reaproveitada.
4. Impedir autoalteração de perfil/status, conforme a proteção já existente no serviço.
5. Preservar o e-mail Google e o histórico do usuário; não criar campo de senha ou credencial local.
6. Reservar exclusão física para procedimento excepcional de retenção/privacidade, com política própria e aprovação explícita — não como ação comum da tela administrativa.

## Pré-requisitos antes de implementar

- Definir se o endpoint DELETE será removido, responderá como desativação lógica, ou será substituído por ação explícita de desativar. Não mudar o significado HTTP sem alinhar o contrato do frontend.
- Injetar um `PostgresAuditSink` na aplicação apenas quando houver conexão PostgreSQL configurada e grants mínimos revisados; não conectar o sink em memória nem criar fallback silencioso.
- Garantir que as alterações de perfil/status só ocorram pelo método transacional auditado, não pelo PUT cadastral legado.
- Rever o PUT legado: hoje `UsuarioInput` aceita perfil/status junto dos dados cadastrais. Antes de liberar qualquer capacidade de atualização, separar os campos cadastrais dos administrativos para que não exista caminho alternativo sem auditoria.
- Adicionar testes HTTP para identidade, permissão, autoalteração, último Admin, auditoria e comportamento de listagem/consulta após desativação.
- Não habilitar capacidades de perfil até aprovação explícita da matriz de permissões.

## Não fazer nesta etapa

- Não alterar a rota DELETE atual nem seu comportamento sem decisão de compatibilidade.
- Não aplicar SQL, migration ou grants.
- Não ativar permissões administrativas.
- Não apagar, importar ou modificar dados reais.
- Não conectar banco de produção.

## Critério de aceite futuro

Uma desativação aprovada deve deixar o registro consultável para auditoria, bloquear autenticação futura do usuário inativo, manter exatamente um Admin ativo ou mais, e confirmar/reverter alteração e evento de auditoria como uma única transação.
