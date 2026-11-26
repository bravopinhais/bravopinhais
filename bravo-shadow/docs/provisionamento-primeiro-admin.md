# Provisionamento seguro do primeiro administrador

## Status

**Desenho técnico, ainda não implementado.** Nenhum Admin foi criado, nenhum segredo foi configurado e nenhuma rota foi alterada. Este documento não autoriza expor a API.

## Problema confirmado

O schema `UsuarioInput` aceita `perfil=Admin` e `status=Ativo`. O router atual permite POST e PUT sem autenticação/autorização. O teste legado `test_create_and_get_profile_by_email` cria um Admin diretamente por HTTP sem token. Portanto, a rota não pode ser usada em ambiente acessível enquanto a proteção não for aplicada.

## Estratégia recomendada

O primeiro Admin deve ser provisionado fora da API pública, por um comando administrativo executado no ambiente controlado de homologação, com estas condições:

1. Exigir PostgreSQL de sombra persistente. Recusar explicitamente o backend `memory`, porque o cadastro desaparece ao reiniciar o processo.
2. Exigir uma variável de ambiente `BRAVO_BOOTSTRAP_ADMIN_EMAIL`, normalizada para minúsculas e validada como endereço de e-mail.
3. O e-mail deve ser informado pelo responsável do ambiente e corresponder à conta Google que será usada. Não escolher o e-mail automaticamente, não inferir pelo primeiro login e não aceitar perfil vindo do navegador.
4. O comando cria somente esse cadastro com `perfil=Admin` e `status=Ativo`; não recebe esses campos como argumentos editáveis.
5. Executar em transação, com bloqueio/garantia de unicidade para impedir duas inicializações concorrentes. Se já houver qualquer Admin ativo, abortar sem modificar registros.
6. Se o e-mail já existir como Operador ou Inativo, abortar e exigir revisão administrativa explícita; nunca elevar ou reativar automaticamente uma conta existente.
7. Registrar auditoria sem token, senha, segredo ou dados pessoais desnecessários: data, resultado e identificador técnico do processo.
8. Após provisionamento bem-sucedido, remover a variável de bootstrap do ambiente e impedir reutilização. O comando deve ser idempotente no sentido seguro: segunda execução não altera nem promove ninguém.
9. A autenticação normal continua sendo Google ID token validado no servidor, e-mail verificado e correspondência exata com o cadastro interno ativo. O bootstrap não substitui essa validação.
10. A API não deve expor endpoint público de bootstrap nem aceitar autoelevação por payload.

## Proteção necessária na API depois do bootstrap

- Separar schemas de criação e atualização de usuário dos campos administrativos. Um usuário comum não pode enviar livremente `perfil` ou `status`.
- Somente uma identidade autenticada que possua capacidade administrativa explícita pode atribuir ou alterar perfil/status.
- Não permitir remover, inativar ou rebaixar o último Admin ativo sem uma operação de transferência confirmada.
- Proteger também GET de lista/detalhe; dados de usuários não são públicos.
- Em qualquer falha de autenticação, autorização, banco ou configuração, negar a operação (fail closed).
- Testar criação, promoção, rebaixamento, inativação, exclusão, concorrência e proteção do último Admin com PostgreSQL local real.

## Ordem de entrega

1. Confirmar este desenho e a matriz funcional de permissões.
2. Implementar o comando de bootstrap exclusivamente para ambiente sombra local/homologação, com transação PostgreSQL e testes.
3. Separar schemas de gestão de usuários e proteger todas as rotas de usuários.
4. Proteger os demais routers por capacidade explícita.
5. Executar testes de integração em banco local descartável.
6. Só depois considerar deploy privado de homologação; nunca apontar para banco ou dados de produção.

## Restrições preservadas

- Sem senha local tradicional; login continua baseado em conta Google/e-mail.
- Sem uso de banco de produção, migration remota ou exposição pública.
- O `index.html` original não deve ser modificado.
- A proposta Admin/Operador continua pendente de aprovação; este documento não concede automaticamente permissões a nenhum perfil.
