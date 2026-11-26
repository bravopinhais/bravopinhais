# Segurança do fluxo de revisão de migração — Bravo Shadow

**Status:** especificação para revisão. Não cria roles, policies, grants ou migrations.
**Escopo:** autenticação do revisor, autorização de operações e isolamento do histórico de revisão.

## 1. Fontes confiáveis de identidade

O fluxo deve reutilizar a autenticação existente em backend/app/core/authentication.py:

1. Receber o Bearer ID token Google.
2. Validar assinatura, emissor, audiência e expiração no servidor.
3. Exigir sub, e-mail e email_verified = true.
4. Vincular o e-mail normalizado a exatamente um usuário Bravo ativo.
5. Construir AuthenticatedPrincipal com subject, e-mail, perfil e status internos.

O navegador nunca escolhe reviewer_id, perfil ou status. O backend deriva o ator exclusivamente do principal autenticado. Para persistência, usar o subject estável como reviewer_id; e-mail pode ser guardado em campo de auditoria separado se houver necessidade aprovada.

## 2. Capacidade dedicada

Adicionar uma capacidade específica, por exemplo migration_review:read e migration_review:append, somente depois da aprovação da matriz de permissões.

A política atual de authorization.py é provisória: Admin possui as capacidades listadas e Operador não recebe concessões. Não presumir que isso autoriza revisão de migração. A decisão sobre quais perfis podem consultar e registrar revisões permanece pendente.

Regras obrigatórias:
- Falha fechada para principal ausente, inativo, perfil desconhecido ou capacidade não concedida.
- Verificação no backend em cada endpoint; esconder botões na interface não é autorização.
- Não expor endpoints de revisão até que as dependências estejam conectadas e testadas.
- initialize é operação administrativa de preparação do lote, não deve ser chamada por endpoint público.
- append exige capacidade específica e justificativa não vazia.
- Nenhuma revisão humana autoriza execução de importação; aprovação operacional do lote é fluxo separado.

## 3. Modelo de acesso ao PostgreSQL

A política de RLS não deve confiar em cabeçalhos HTTP ou parâmetros enviados pelo cliente.

Antes de escrever policies, escolher e validar uma das estratégias:

### Estratégia A — conexão backend com contexto transacional
- O backend autentica e autoriza o principal.
- Dentro da mesma transação, define contexto local de ator e operação usando parâmetros seguros.
- Policies verificam esse contexto, que deve ser impossível de forjar por acesso direto do cliente.
- O contexto é limpo automaticamente ao fim da transação.

### Estratégia B — autorização integral na camada de serviço
- Apenas role privada do backend acessa o schema.
- A aplicação faz todas as verificações de identidade e capacidade.
- RLS continua ativa como defesa adicional, com policies estritas e sem grants a anon/authenticated.
- A role não pode ser superuser nem possuir BYPASSRLS.

Nenhuma estratégia está aprovada. Não misturar as duas sem definir claramente o modelo de ameaça. Não usar service_role como atalho e não desabilitar RLS.

## 4. Matriz de operações proposta

| Operação | Acesso pretendido | Condição |
|---|---|---|
| Consultar lote e fila | leitura autenticada autorizada | lote e manifesto conferidos |
| Consultar histórico | leitura autenticada autorizada | acesso restrito ao lote |
| Inicializar fotografia | serviço interno de preparação | manifesto verificado; sem endpoint público |
| Registrar revisão | revisor autenticado autorizado | subject do principal, versão esperada e justificativa |
| Alterar/excluir evento | negado | correção somente por novo evento |
| Aplicar/importar lote | fora deste adaptador | aprovação operacional separada e explícita |

## 5. Isolamento e integridade

- Toda consulta deve filtrar por batch_key e conferir manifest_hash.
- A fotografia de decisões deve ser comparada integralmente com o registro determinístico reconstruído.
- O banco deve manter unicidade de event_id e de (batch_key, decision_id, version).
- A inclusão deve bloquear a linha da decisão com FOR UPDATE e inserir evento na mesma transação.
- A role de runtime não recebe UPDATE ou DELETE nos eventos.
- A role de runtime não deve criar schemas, tabelas, policies ou grants.
- Nenhum dado de lote pode ser consultado por usuário não autorizado apenas por conhecer seu identificador.

## 6. Testes de segurança obrigatórios antes de habilitar

1. Sem token: 401.
2. Token inválido/expirado: 401.
3. E-mail não verificado, usuário inexistente ou inativo: acesso negado.
4. Perfil sem capacidade: 403.
5. Cliente tenta enviar reviewer_id de terceiro: campo ignorado ou requisição rejeitada; ator persistido continua sendo o subject autenticado.
6. Consulta de outro lote: sem acesso.
7. Manifesto divergente ou fotografia alterada: falha fechada.
8. Duas gravações concorrentes para mesma versão: apenas uma vence.
9. Tentativa de UPDATE/DELETE de evento pela role de runtime: negada pelo banco.
10. Acesso via anon e authenticated: negado.
11. Rollback em falha de inserção: nenhum evento parcial permanece.
12. Revisor autorizado não recebe, por isso, permissão para executar importação.

Os testes de RLS devem rodar em PostgreSQL local com roles reais de teste, não apenas em mocks Python.

## 7. Decisões ainda necessárias

- Aprovar quais perfis Bravo podem consultar e registrar revisões.
- Escolher estratégia de contexto/RLS após validar o modelo de conexão.
- Definir se o histórico guarda apenas Google sub ou também e-mail de auditoria.
- Definir role privada e grants mínimos em ambiente local.
- Conectar as dependências de autorização somente após aprovação da matriz.

## 8. Estado e limites

A autenticação Google e a autorização central existentes ainda não protegem todas as rotas de negócio. Este documento não declara o sistema seguro nem habilita endpoints. O adaptador PostgreSQL continua desconectado; o SQL continua rascunho; RLS não recebeu policies ou grants; nenhuma migration foi aplicada.

A próxima entrega segura é revisar o desenho de roles e testar o comportamento de RLS localmente com dados sintéticos, depois de a matriz de permissões ser aprovada. O login e sua aparência continuam fora deste escopo.
