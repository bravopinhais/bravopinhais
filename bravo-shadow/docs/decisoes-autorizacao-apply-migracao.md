# Decisões de arquitetura — autorização de apply de migração

**Status:** decisões para implementação futura; não habilitam gravação.  
**Branch:** `bravo-shadow`.

## 1. Ambiente canônico

A máquina de estados `migration_batch_state.py` define os ambientes permitidos:

- `local_disposable`: único ambiente elegível a apply transacional persistente.
- `ci_ephemeral`: validações automatizadas e descartáveis; sem autorização de apply.

O valor `shadow_local` usado em `MigrationApplyAuthorization` é incompatível com a máquina de estados e com o DDL. Deve ser removido/substituído no próximo pacote de código. Não adicionar `shadow_local` ao banco para acomodar o núcleo Python.

O adapter deverá conferir o ambiente armazenado no lote, não confiar apenas no valor enviado pelo chamador.

## 2. Execução persistida

Criar `bravo_shadow.migration_executions` com:
- `execution_id` globalmente único;
- `batch_id` e `manifest_hash`;
- `plan_sha256`;
- `environment`, restrito a `local_disposable`;
- `requested_by_subject`, vindo do principal Google autenticado;
- estado e timestamps de criação/início/fim;
- unicidade de `(batch_id, plan_sha256)`, impedindo nova execução do mesmo plano para contornar falha ou resultado incerto.

A execução é criada antes da aprovação e fica vinculada ao manifesto e ao plano imutáveis. Não registrar payload de origem na tabela.

## 3. Aprovação específica de apply

Criar `bravo_shadow.migration_apply_approvals`:
- uma decisão final append-only por execução;
- vinculação por `execution_id`, `batch_id`, `manifest_hash` e `plan_sha256`;
- decisão `approved` ou `rejected`;
- `reviewer_subject`, justificativa e timestamp;
- aprovador diferente de `requested_by_subject`.

A aprovação é específica para o plano exato. Qualquer alteração de manifesto/plano exige nova execução e nova aprovação. Uma rejeição não pode ser sobrescrita. A aprovação anterior do manifesto para dry-run e os campos genéricos `approved_*` do lote não autorizam apply.

## 4. Identidade do ator

O ator da execução e o ator da auditoria vêm de `AuthenticatedPrincipal.subject`, que corresponde ao `sub` do ID token Google validado pelo backend. O backend já exige e-mail verificado e vínculo único com usuário interno ativo.

Regras:
- nunca aceitar `actor_subject`, `requested_by_subject` ou `reviewer_subject` do payload do registro importado;
- resolver solicitante/aprovador a partir do principal autenticado em operações distintas;
- inserir auditoria de sucesso na mesma transação de negócio e proveniência;
- manter dados de origem e dados pessoais fora da auditoria.

## 5. Ordem de autorização do apply

1. Autenticar o solicitante e validar capacidade administrativa específica de migração (ainda não implementada).
2. Bloquear lote; conferir ambiente `local_disposable`, status `approved`, manifesto e estado elegível.
3. Bloquear execução; conferir lote, manifesto, plano e estado.
4. Ler aprovação append-only e exigir decisão `approved`, com hash idêntico.
5. Exigir aprovador distinto do solicitante.
6. Bloquear identidade de origem, validar destino e efetuar as três gravações atômicas: negócio, proveniência e auditoria.
7. Atualizar o estado da execução e, ao concluir lote, atualizar estado do lote em transação própria sob lock.

A autorização em memória do núcleo Python nunca é suficiente isoladamente. A fonte de verdade é a aprovação persistida e validada dentro da transação.

## 6. O que ainda não está autorizado

- Não executar DDL nem gerar migration aplicável.
- Não criar roles, grants, policies ou conexões.
- Não ligar endpoint/rota ou habilitar apply no composition root.
- Não importar dados reais nem fazer dual-write.
- Não alterar produção ou a branch `main`.

A próxima implementação deve alinhar o modelo Python, o contrato do store e o SQL ao DDL rascunhado; incluir allowlist explícita de tabelas de destino; manter o apply desligado até revisão independente.
