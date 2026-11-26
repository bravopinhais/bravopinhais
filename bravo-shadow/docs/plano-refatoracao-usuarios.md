# Plano de refatoração do módulo Usuários — Bravo Shadow

## Status

Plano técnico detalhado, ainda não implementado. Foi elaborado após leitura dos schemas, serviço, router, contrato de gestão e desenho de bootstrap. Não altera código, dados, rotas, autenticação, permissões ou interface.

## Diagnóstico confirmado

O módulo atual usa um único modelo de entrada para criação e atualização. Esse modelo contém simultaneamente dados cadastrais (e-mail, nome, loja e cargo) e campos privilegiados (perfil e status).

O serviço usa o mesmo objeto para criar e substituir integralmente um registro. O router expõe lista, detalhe, POST, PUT e DELETE sem dependências de autenticação/autorização. A exclusão é física. O repositório padrão é em memória.

Consequência: não é seguro apenas adicionar uma dependência genérica ao router atual. Primeiro é necessário separar os contratos e as operações administrativas.

## Contratos-alvo propostos

Os nomes são sugestões para implementação futura.

### 1. UsuarioCadastroInput

Campos permitidos: email, nome, loja e cargo.

Não aceitar: perfil, status, id, subject Google, token, senha ou hash de senha.

Manter validação de e-mail normalizado, remoção de espaços excedentes e extra=forbid.

**Regra:** alteração do e-mail não deve ocorrer no fluxo cadastral comum. A identidade está vinculada ao e-mail verificado da conta Google; eventual troca exige fluxo próprio de reconciliação, confirmação e auditoria.

### 2. UsuarioCadastroUpdate

Atualização parcial dos campos cadastrais autorizados. Campo omitido significa “preservar valor atual”; campo enviado vazio deve ser rejeitado quando obrigatório. Não aceitar perfil ou status.

### 3. UsuarioAdministracaoUpdate

Contrato separado, contendo apenas os campos administrativos que forem aprovados: perfil, limitado aos perfis internos conhecidos; status, limitado aos estados aprovados.

Este contrato exige capacidade administrativa específica, validação contextual, auditoria e transação. Não deve ser reaproveitado no endpoint de edição cadastral.

### 4. UsuarioRead

Modelo de saída explícito. Não retornar credenciais, tokens, dados de autenticação ou campos internos desnecessários. A seleção de campos de resposta deve ser revisada junto com a política de privacidade e a capacidade usuarios:read.

## Operações e rotas-alvo

As rotas abaixo são uma proposta de contrato, não estão implementadas.

| Método e rota | Operação | Controle pretendido |
|---|---|---|
| GET /api/v1/usuarios | Listar usuários | Identidade válida + usuarios:read |
| GET /api/v1/usuarios/{id} | Consultar usuário | Identidade válida + usuarios:read |
| POST /api/v1/usuarios | Criar cadastro sem privilégio escolhido pelo cliente | Identidade válida + usuarios:create; estado inicial definido pelo servidor após decisão de onboarding |
| PATCH /api/v1/usuarios/{id}/dados | Alterar dados cadastrais | Identidade válida + usuarios:update_data |
| PATCH /api/v1/usuarios/{id}/administracao | Alterar perfil/status | Identidade válida + usuarios:update_profile e/ou usuarios:update_status, conforme campos |
| POST /api/v1/usuarios/{id}/desativar | Desativar conta | Identidade válida + usuarios:deactivate |
| DELETE /api/v1/usuarios/{id} | Não recomendado como fluxo padrão | Preferir desativação lógica e retenção; decisão final pendente |

Não manter um PUT integral que aceite campos cadastrais e administrativos no mesmo payload. Quando o contrato novo estiver pronto, rotas legadas devem ser removidas ou responder com erro explícito após período de migração controlado; nunca continuar aceitando perfil/status no payload antigo.

## Regras transacionais e contextuais

1. Autoalteração: a identidade autenticada não pode alterar o próprio perfil ou status.
2. Último Admin: não permitir desativar, rebaixar ou excluir o último Admin ativo.
3. Concorrência: a contagem de Admins ativos e a alteração devem ocorrer na mesma transação com bloqueio apropriado, evitando duas operações simultâneas que removam a última conta administrativa.
4. Unicidade: e-mail normalizado deve ter unicidade garantida no banco, não apenas checagem prévia em Python.
5. Auditoria: mudança de perfil/status e desativação devem gravar evento append-only na mesma transação da alteração. Se a auditoria falhar, a operação deve fazer rollback.
6. Identidade: o ator vem exclusivamente do principal construído após validação do Google ID token e resolução do cadastro ativo.
7. Falha fechada: usuário ausente/inativo, perfil desconhecido, capacidade ausente, conflito ou erro de persistência nunca deve resultar em concessão.
8. Sem promoção implícita: criação não aceita perfil Admin; bootstrap inicial permanece fora da API conforme documento próprio.
9. Sem senha local: não adicionar campos de senha, hash ou fluxo alternativo de login.

## Decisões funcionais ainda pendentes

Não codificar valores padrão nem comportamento até o responsável aprovar:

- Novo cadastro inicia como Ativo, Inativo ou Pendente?
- Haverá convite ou aprovação antes do primeiro acesso?
- Quem poderá criar um usuário?
- Operador poderá consultar lista de usuários ou apenas seu próprio cadastro?
- Exclusão física será proibida em definitivo ou haverá exceção formal de retenção?
- Quais campos cadastrais podem ser alterados após a primeira autenticação?
- Quais ações administrativas exigem confirmação adicional?

## Plano de testes antes de ativação

### Schemas
- Rejeitar perfil, status, id e campos extras em cadastro/edição.
- Normalizar e-mail e texto.
- Rejeitar e-mail inválido e campos obrigatórios em branco.
- Confirmar que campo omitido em PATCH preserva o valor.

### Serviço e transações
- Criar usuário sem aceitar privilégio do cliente.
- Rejeitar e-mail duplicado, inclusive concorrente no PostgreSQL.
- Impedir alteração do próprio perfil/status.
- Impedir desativação/rebaixamento do último Admin ativo.
- Confirmar rollback quando auditoria falhar.
- Confirmar que desativação preserva referências e histórico.

### HTTP
- Sem token: 401.
- Token inválido, expirado ou audiência incorreta: 401.
- Usuário sem cadastro ativo: negar.
- Sem capacidade adequada: 403.
- Capacidade correta: permitir apenas a operação correspondente.
- Tentar enviar campos administrativos na rota cadastral: 422.
- Verificar que respostas não expõem credenciais ou dados internos.

### Banco local
Executar somente em PostgreSQL local descartável, após migration revisada. Não usar projeto remoto, banco de produção ou --remote.

## Ordem recomendada

1. Aprovar decisões de onboarding e matriz de capacidades.
2. Implementar schemas separados e testes unitários.
3. Implementar métodos de serviço distintos para cadastro, atualização cadastral, alteração administrativa e desativação.
4. Definir restrições de unicidade e transação para último Admin.
5. Integrar auditoria na mesma transação.
6. Proteger cada rota com Google ID token validado e capacidade específica.
7. Executar testes HTTP e PostgreSQL local.
8. Fazer revisão independente antes de qualquer homologação privada.

## Estado preservado

O módulo continua no estado atual, sem mudanças de código nesta etapa. Não há autorização para exposição pública, conexão com dados reais ou promoção de usuários. O sistema original e a tela de login permanecem intocados.
