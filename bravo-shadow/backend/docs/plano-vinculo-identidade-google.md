# Plano controlado de vínculo da identidade Google

**Estado: proposta técnica; não implementada e não autorizada para ativação.**

## Objetivo

Evoluir da descoberta inicial por e-mail verificado para uma identidade persistente baseada no claim Google `sub`, sem permitir que uma conta Google diferente assuma um cadastro existente por coincidência de e-mail.

Este plano não altera a autenticação atual, não cria rotas, não aplica migrations e não concede capacidades.

## Estado atual verificado

- `verify_google_id_token` valida o ID token no servidor usando o `GOOGLE_CLIENT_ID` configurado.
- `principal_from_google_claims` exige `sub`, e-mail textual e `email_verified is True`.
- O cadastro interno é localizado pelo e-mail normalizado e deve ter correspondência única e status Ativo.
- O `sub` validado é usado no principal e na auditoria, mas não está persistido no cadastro.
- O repositório PostgreSQL de usuários ainda não tem contrato de vínculo Google.
- A autenticação não está conectada ao navegador; o contrato de sessão continua sendo apenas especificação.
- A matriz de capacidades permanece vazia para Admin e Operador.

## Modelo de identidade proposto

1. Adicionar `google_subject` opcional e nullable ao modelo interno de usuário.
2. Impor unicidade global para valores não nulos, preferencialmente por índice único parcial.
3. Depois da vinculação, localizar a conta exclusivamente pelo `sub`; e-mail passa a ser atributo de contato e conferência, não chave de identidade.
4. Nunca preencher `google_subject` automaticamente durante login, importação ou coincidência de e-mail.
5. Não permitir que o cliente envie ou escolha o `sub` que será associado.
6. Uma conta Google já vinculada a outro cadastro deve ser recusada sem tentativa de reassociação automática.

## Fluxo de vinculação assistida

A implementação futura deverá ser uma operação separada do login normal:

1. Exigir sessão Google validada pelo backend e cadastro interno elegível.
2. Exigir autorização administrativa específica, ainda não existente nem concedida.
3. Exigir confirmação de titularidade e revisão do cadastro-alvo por procedimento administrativo fora do fluxo de login.
4. Revalidar no servidor o `sub` e o e-mail verificado; ignorar qualquer identidade enviada no corpo da requisição.
5. Executar em transação: bloquear o cadastro-alvo, verificar que está ativo, confirmar que não há outro cadastro com o mesmo `sub`, gravar o vínculo e inserir evento de auditoria na mesma transação.
6. Se a auditoria falhar, reverter o vínculo. Se houver conflito de unicidade, retornar conflito sem alterar nenhum cadastro.
7. Tornar a operação idempotente somente quando o mesmo `sub` já estiver vinculado ao mesmo cadastro; qualquer divergência deve falhar fechada.

A operação deverá registrar ator, cadastro-alvo, ação, resultado e request ID. Não registrar ID token, credenciais, nem conteúdo desnecessário do perfil.

## Comportamento do login após a evolução

- `sub` vinculado a um cadastro ativo: autenticar esse cadastro.
- `sub` vinculado a cadastro inativo: negar acesso.
- `sub` desconhecido: negar acesso com orientação para processo administrativo; não procurar e vincular automaticamente pelo e-mail.
- E-mail alterado, mas `sub` já vinculado: manter a identidade do cadastro e tratar a atualização do e-mail como fluxo cadastral separado.
- E-mail coincidente com outro cadastro, mas `sub` diferente: negar; nunca assumir o cadastro por e-mail.
- Mesmo `sub` associado a mais de um cadastro: situação impossível após a constraint; se detectada em dados legados, bloquear e exigir saneamento manual.

## Migração e implantação seguras

1. Implementar primeiro modelo, repositório e testes unitários, sem executar migration.
2. Revisar SQL da migration e constraint em ambiente isolado.
3. Executar integração somente no banco descartável dedicado `bravo_shadow_test`, com a trava explícita de testes destrutivos.
4. Validar rollback conjunto entre vínculo e auditoria, concorrência de duas tentativas e conflito de unicidade.
5. Submeter a migration para aprovação separada antes de qualquer aplicação em ambiente persistente.
6. Fazer inventário autorizado dos cadastros sem vínculo; não preencher valores por inferência, e-mail ou dados reais não aprovados.
7. Habilitar a vinculação somente após aprovação explícita da política administrativa, da origem de prova de titularidade e do procedimento de recuperação.

## Matriz mínima de testes futuros

- ID token sem `sub`, e-mail inválido ou `email_verified` diferente de `True`: negar.
- `sub` vinculado ao cadastro ativo: resolver por `sub`, inclusive após mudança de e-mail.
- E-mail coincidente com cadastro existente e `sub` desconhecido/diferente: negar sem vínculo automático.
- `sub` já associado a outro cadastro: conflito, sem mutação.
- Cadastro-alvo inativo: negar.
- Duas vinculações concorrentes para o mesmo `sub`: somente uma pode concluir.
- Falha ao gravar auditoria: rollback do vínculo.
- Repetição do mesmo vínculo para o mesmo cadastro: comportamento idempotente e auditado conforme política aprovada.
- Cliente tentando informar `google_subject` no cadastro/edição comum: rejeitar campo extra.
- Login por senha local: não deve existir nem ser reintroduzido.

## Fora do escopo desta etapa

- Alterar a tela de login ou integrar Google Identity Services no navegador.
- Criar client ID, configurar origens OAuth ou armazenar segredos no repositório.
- Aplicar migrations, alterar schema persistente ou conectar produção.
- Conceder capacidades Admin/Operador ou ativar rotas de usuários.
- Importar, migrar ou vincular cadastros reais.
- Realizar cutover ou dual-write.

**Critério de saída:** esta proposta só poderá virar implementação após aprovação explícita do procedimento de vinculação e recuperação. A autenticação por e-mail atual permanece limitada e não deve ser tratada como vínculo definitivo de identidade.
