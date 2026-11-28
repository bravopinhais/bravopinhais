# Plano de vínculo persistente da identidade Google

## Estado

**Planejamento técnico — não implementado e não autorizado para produção.**

O backend atualmente valida o Google ID token, exige `sub` não vazio e e-mail verificado, e resolve exatamente um cadastro Bravo ativo pelo e-mail normalizado. O valor `sub` é colocado no principal autenticado e usado em auditoria, mas ainda não é persistido como vínculo imutável no cadastro.

Este documento define a próxima evolução para a branch `bravo-shadow`. Não cria migrations, não altera tabelas, não grava identidades e não autoriza importação de dados.

## Objetivo e invariantes

1. Uma identidade Google é identificada pelo par estável `(issuer, sub)`; para o fluxo atual, o issuer aceito deve ser validado pelo verificador Google.
2. Um vínculo persistido aponta para exatamente um cadastro interno Bravo.
3. Um cadastro Bravo pode ter no máximo uma identidade Google ativa vinculada, salvo decisão explícita futura de produto.
4. O vínculo nunca é criado ou trocado automaticamente apenas porque o e-mail atual coincide.
5. E-mail é atributo mutável e meio de descoberta inicial; não é chave permanente de identidade.
6. Perfil, status e capacidades continuam vindo exclusivamente do cadastro interno.
7. Cadastro inexistente, inativo, duplicado, vínculo conflitante ou identidade sem vínculo válido falha fechado.
8. Nenhum endpoint público permite reivindicar, transferir, remover ou substituir vínculos.
9. Nenhum segredo OAuth é armazenado; o Client ID continua sendo configuração pública de audiência, e nenhum Client Secret vai ao frontend ou repositório.

## Modelo de dados proposto

A implementação deve primeiro verificar o schema real e as migrations existentes. Após revisão, preferir colunas dedicadas no cadastro interno ou uma tabela de vínculo separada com restrições equivalentes.

Campos lógicos mínimos:
- `google_issuer`: emissor canônico validado.
- `google_subject`: claim `sub` opaco, tratado como texto e nunca normalizado.
- `google_linked_at`: instante UTC de vinculação.
- `google_linked_by`: identidade administrativa que autorizou a operação, quando aplicável.
- `google_link_status`: estado explícito, se o desenho exigir histórico/revogação.

Restrições obrigatórias no banco:
- unicidade global de `(google_issuer, google_subject)`;
- unicidade de vínculo ativo por cadastro Bravo;
- chaves estrangeiras e regras de exclusão que impeçam órfãos;
- índices para resolução por identidade;
- transação atômica para vincular e auditar.

Não usar e-mail como índice único da identidade Google. Não permitir que a mesma identidade seja associada a dois cadastros.

## Fluxo de autenticação depois da implementação

1. Validar criptograficamente o ID token no servidor: assinatura, issuer, audience, expiração e claims obrigatórios.
2. Exigir `email_verified is True`, `sub` não vazio e issuer pertencente à lista oficial aceita.
3. Procurar primeiro o vínculo persistido por `(issuer, sub)`.
4. Se encontrado, carregar o cadastro Bravo apontado e exigir status `Ativo`. O e-mail do token pode ter mudado; não trocar o vínculo nem o cadastro automaticamente.
5. Se não encontrado, não conceder acesso por simples correspondência de e-mail. Encaminhar para fluxo controlado de vinculação inicial.
6. Em toda resposta autenticada, obter perfil e capacidades atuais do cadastro interno.

## Vinculação inicial e recuperação

O primeiro vínculo deve ser um processo administrativo controlado, fora de autoatendimento público:
- confirmar a titularidade da conta Google por autenticação recente;
- confirmar a identidade do cadastro Bravo por procedimento administrativo independente;
- exigir aprovação de Admin autorizado, sem permitir que o próprio usuário eleve privilégios;
- executar gravação do vínculo e evento de auditoria na mesma transação;
- recusar se já houver vínculo para o cadastro ou para o `sub`;
- registrar ator, alvo, motivo, horário e request ID, sem registrar token;
- oferecer procedimento de recuperação com dupla verificação e trilha de auditoria.

A troca de conta Google, perda de acesso ou alteração de e-mail não deve provocar desvinculação automática. Deve exigir recuperação administrativa, autenticação reforçada e auditoria.

## Testes obrigatórios

- identidade vinculada e cadastro ativo: acesso permitido;
- identidade vinculada e cadastro inativo: acesso negado;
- identidade vinculada a outro cadastro: conflito e negação;
- cadastro com vínculo diferente: negação, sem sobrescrita;
- mesmo `sub` com e-mail alterado: mantém o cadastro já vinculado;
- e-mail coincidente sem vínculo: não cria vínculo nem concede acesso;
- issuer inválido, ausente ou não aceito: negação;
- `sub` ausente/vazio: negação;
- concorrência de duas tentativas de vinculação: somente uma vence por restrição transacional;
- falha ao gravar auditoria: rollback integral do vínculo;
- nenhum token, código OAuth ou segredo aparece em logs;
- rotas administrativas de vínculo sem autorização explícita: 401/403.

Os testes de concorrência e unicidade devem usar PostgreSQL descartável e conexões independentes; mocks isolados não comprovam as restrições do banco.

## Plano de entrega

1. Inventariar migrations, schema, adapters e estratégia de auditoria existentes.
2. Revisar o modelo de dados e as restrições com testes de migração em PostgreSQL descartável.
3. Implementar repositório e serviço de vínculo, sem endpoint público de autoassociação.
4. Implementar operação administrativa protegida e auditada.
5. Alterar a autenticação para priorizar `(issuer, sub)` e negar vínculo ausente.
6. Executar suíte unitária, integração PostgreSQL, cobertura de rotas e testes de concorrência.
7. Atualizar documentação operacional e procedimento de recuperação.
8. Só depois de homologação separada avaliar implantação de preview com dados sintéticos.

## Critérios de bloqueio

Não prosseguir para dados reais, produção ou cutover enquanto:
- não houver restrições de unicidade efetivas no PostgreSQL;
- não houver auditoria atômica e recuperação revisada;
- o modelo de bootstrap/vinculação administrativa não estiver aprovado;
- a homologação não demonstrar negação de todos os cenários conflitantes.

**Este plano não altera o fluxo de login atual e não autoriza importar, vincular ou modificar contas reais.**
