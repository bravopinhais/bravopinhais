# Evolução do vínculo de identidade Google — Bravo Shadow

**Status: decisão técnica proposta; ainda não implementada.** A autenticação atual valida o ID token Google e associa o cadastro interno pelo e-mail verificado. Não há coluna persistida para o claim `sub`.

## Evidência técnica

O verificador `verify_oauth2_token` valida assinatura, emissor, audiência e expiração. A API exige `email_verified=true`, normaliza o e-mail e procura exatamente um usuário interno ativo. O `sub` validado é retornado no principal da requisição, mas não é persistido nem usado na próxima identificação.

A documentação oficial do Google recomenda usar `sub` como identificador único e estável da Conta Google; o endereço de e-mail pode mudar. Portanto, a associação atual por e-mail é adequada como etapa inicial de descoberta, mas não deve ser considerada o vínculo definitivo de identidade. Referência: https://developers.google.com/identity/gsi/web/guides/verify-google-id-token?hl=pt-br

## Evolução recomendada

1. Adicionar ao modelo de usuário um campo opcional `google_subject` (claim `sub`), sem preencher automaticamente os registros existentes.
2. Criar índice único parcial para valores não nulos de `google_subject`, evitando que a mesma Conta Google seja vinculada a mais de um cadastro.
3. Quando houver `google_subject` persistido, localizar a conta por esse identificador; conferir também o e-mail verificado como atributo de contato atualizado, não como chave primária.
4. Para usuários ainda sem vínculo, exigir processo explícito e auditado de associação. Não vincular automaticamente apenas porque o e-mail do token coincide com o e-mail cadastrado.
5. Tratar troca de e-mail como atualização do atributo após validar o mesmo `sub`; nunca permitir que um novo `sub` assuma um cadastro existente por coincidência de e-mail.
6. Definir procedimento assistido para recuperação de conta ou troca de Conta Google, com validação administrativa fora do fluxo normal de login.

## Migração segura

- Manter a coluna inicialmente nullable para não bloquear os perfis existentes.
- Fazer inventário apenas de registros autorizados/anônimos no ambiente de teste; não importar dados reais nesta etapa.
- Vincular contas existentes somente após processo aprovado e evidência suficiente de titularidade.
- Não alterar a tela de login nem introduzir senha local.
- Não habilitar rotas/capabilities, executar migrations, conectar banco de produção ou realizar cutover como parte desta proposta.

## Critérios para implementação futura

- Teste de identidade já vinculada por `sub`, mesmo após mudança do e-mail verificado.
- Teste de rejeição quando o e-mail coincide, mas o `sub` é diferente.
- Teste de rejeição de `sub` já vinculado a outro usuário.
- Teste de associação inicial somente pelo fluxo explícito e auditado.
- Teste de usuário inativo e de token sem e-mail verificado.
- Integração PostgreSQL em banco descartável com índice único parcial e rollback de auditoria.

Até que esses critérios sejam implementados e aprovados, a associação permanece baseada em e-mail verificado e esta limitação deve ser considerada antes de qualquer ativação operacional.
