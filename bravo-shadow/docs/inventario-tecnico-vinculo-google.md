# Inventário técnico — vínculo persistente da identidade Google

## Escopo e segurança

Documento de inventário da branch `bravo-shadow`. Não cria nem executa DDL, não altera dados, não cria endpoints e não autoriza conexão com banco real ou importação. A análise considera exclusivamente os arquivos versionados e os testes da homologação descartável.

## Estado observado

### Cadastro interno

A migração `supabase/migrations/20261127000100_bravo_shadow_core.sql` cria `bravo_shadow.usuarios` com:

- `id`, `email`, `nome`, `loja`, `cargo`, `perfil`, `status`;
- campos técnicos `created_at`, `updated_at`, `version`;
- índice único `usuarios_email_ci_uidx` em `lower(btrim(email))`;
- RLS habilitado, sem policies ou grants de cliente nesta fase.

Não existem colunas `google_issuer`, `google_subject` ou metadados de vínculo nessa tabela. O repositório PostgreSQL seleciona explicitamente as sete colunas cadastrais e resolve identidade por e-mail normalizado, limitando a busca a dois resultados para detectar duplicidade.

### Autenticação atual

O backend valida assinatura, emissor, audiência e expiração do ID token Google; exige `sub`, e-mail textual e `email_verified=true`. Em seguida, associa por e-mail verificado a exatamente um usuário interno com status `Ativo`. O `sub` é colocado no principal autenticado e usado como identificador do ator na auditoria, mas não é persistido como vínculo de conta.

Consequência: a associação atual depende do e-mail. Não deve ser descrita como vínculo Google permanente nem como proteção contra alteração ou reciclagem de e-mail.

### Auditoria

A migração `20261127000200_bravo_shadow_audit.sql` cria `bravo_shadow.audit_events`, com `actor_subject` obrigatório e RLS habilitado + FORCE. O adaptador `PostgresAuditSink` oferece gravação append-only e usa a conexão transacional fornecida pelo serviço. O valor de `actor_subject` é evidência do principal que executou a ação; não substitui uma tabela de identidade vinculada ao usuário interno.

## Requisitos para a próxima implementação

1. Definir se o vínculo será armazenado na própria tabela `usuarios` ou em tabela relacional dedicada. A escolha deve considerar histórico, recuperação, múltiplas identidades e exclusão lógica.
2. Fixar a identidade por par `(issuer, sub)`, não pelo e-mail. Validar explicitamente o emissor permitido e preservar o `sub` como identificador opaco.
3. Impor unicidade no banco tanto para identidade Google quanto para conta Bravo, com tratamento transacional de concorrência.
4. Exigir operação administrativa autenticada e auditada para o vínculo inicial; coincidência de e-mail, sozinha, não pode criar vínculo automaticamente.
5. Definir recuperação, desvinculação e troca de identidade sem permitir autoelevação ou reassociação por e-mail.
6. Separar credenciais/roles de migração e runtime. O runtime não pode receber DDL, alteração de vínculo estrutural ou privilégios administrativos de banco.
7. Criar migração versionada apenas após revisão da decisão de modelagem, seguida de testes em PostgreSQL descartável.

## Matriz mínima de testes antes de habilitar

- Identidade vinculada + conta interna Ativa: acesso permitido.
- Identidade vinculada + conta Inativa: acesso negado.
- Mesmo `sub` tentando apontar para outra conta: conflito e auditoria.
- Outra identidade tentando ocupar conta já vinculada: conflito e auditoria.
- E-mail alterado no Google após vínculo: manter a conta original; nunca reassociar.
- Mesmo e-mail sem vínculo persistente: não conceder acesso automático.
- Emissor inesperado, `sub` ausente ou token inválido: negar.
- Duas tentativas concorrentes de vincular a mesma identidade/conta: apenas uma vence.
- Falha de auditoria: rollback integral do vínculo.
- Nenhum token bruto ou segredo nos logs.

## Bloqueios explícitos

Até completar a revisão e homologação:

- manter o fluxo atual de autenticação por e-mail apenas como comportamento já implementado, sem alegar persistência de `sub`;
- não aplicar migração em Supabase remoto;
- não configurar credenciais reais no projeto de hospedagem;
- não importar cadastros reais;
- não liberar API para uso funcional ou alterar a aplicação de produção.
