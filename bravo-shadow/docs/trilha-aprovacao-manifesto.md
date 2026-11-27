# Trilha de evidências e aprovação do manifesto

**Branch:** `bravo-shadow`  
**Status:** verificador puro e DDL de referência; nenhuma persistência foi criada ou executada.

## Finalidade

Registrar uma decisão humana sobre um manifesto específico, vinculando a decisão aos três identificadores de evidência:
- SHA-256 do manifesto canônico;
- SHA-256 dos bytes originais;
- `snapshotHash` do envelope.

A decisão `approved_for_dry_run` significa exclusivamente que o manifesto pode avançar para um dry-run em ambiente descartável/efêmero. Não aprova lote, não altera máquina de estados, não autoriza escrita e não executa importação.

## Decisões aceitas

- `approved_for_dry_run`: elegível para a próxima etapa de dry-run somente se o manifesto estiver `awaiting_human_approval`, sem gates e com integridade estrutural limpa;
- `rejected`: revisão rejeitada;
- `request_changes`: exige correção e novo manifesto.

Cada evento é imutável e recebe sequência por manifesto. Uma nova revisão cria novo evento; não atualiza nem apaga o anterior.

## Identidade e autenticação

O campo `reviewer_id` deve ser o identificador interno Bravo obtido após autenticação Google e validação de usuário interno único com status Ativo. O verificador Python apenas valida a forma e a vinculação da evidência: não autentica a pessoa e não deve ser exposto como endpoint de aprovação.

## Segurança e persistência

O SQL é somente rascunho. Inclui hashes, sequência, justificativa, data com fuso, restrição de escopo e bloqueio de UPDATE/DELETE/TRUNCATE por trigger. RLS fica habilitado e sem grants/policies; portanto, acesso permanece fechado até desenho e aprovação de privilégios finais.

A implementação futura deve inserir sob lock, impor sequência monotônica e idempotência por `event_id`. A identidade autenticada e o manifesto persistido devem ser revalidados na mesma transação.

## Separação obrigatória de etapas

1. Manifesto construído e bloqueios avaliados.
2. Aprovação documental para dry-run.
3. Dry-run isolado e reconciliação dos resultados.
4. Aprovação independente do lote, vinculada ao mesmo manifesto.
5. Qualquer aplicação real exige autorização expressa separada e revisão de segurança.

A etapa 2 não substitui a etapa 4 nem a 5. O estado atual do manifesto continua `blocked`, portanto não pode receber decisão válida de aprovação para dry-run.

## Limites atuais

Não há endpoint, UI, conexão, tabela criada, role, grant ou policy implementados para esta trilha. Nenhum banco foi acessado. Os testes sintéticos foram adicionados, mas não executados.
