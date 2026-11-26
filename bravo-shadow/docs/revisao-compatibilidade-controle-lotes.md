# Revisão de compatibilidade — controle de lotes e proveniência

**Data:** 26/11/2026  
**Branch:** `bravo-shadow`  
**Escopo:** inspeção estática dos arquivos versionados; nenhuma conexão foi aberta e nenhum SQL foi executado.

## 1. Resultado da inspeção do repositório

- `bravo-shadow/supabase/README.md` declara que ainda não há `config.toml`/`config.jsonc`, migration oficial, banco iniciado ou seed local.
- O SQL funcional existente está em `docs/sql-piloto-financeiro.sql` e permanece identificado como rascunho.
- O backend cria conexão PostgreSQL somente quando `BRAVO_STORAGE_BACKEND=postgres` e a fábrica é chamada; o padrão documentado continua `memory`.
- O modo PostgreSQL atual liga os adaptadores dos módulos de negócio; não é um adaptador exclusivo do importador.
- A integração CI usa PostgreSQL 16 efêmero para testes do ledger de revisão. A fixture desses testes cria as roles `anon`, `authenticated` e `service_role` antes de aplicar o SQL específico do ledger.
- O workflow não aplica `sql-controle-lotes-importacao-rascunho.sql`; portanto, o sucesso da suíte PostgreSQL existente não valida esse DDL.

## 2. Compatibilidade observada

| Item | Situação | Consequência |
|---|---|---|
| Versão do PostgreSQL | PostgreSQL 16 em CI para testes existentes | Boa referência para futura validação; não prova compatibilidade do DDL novo. |
| Supabase local | Não inicializado/versionado | Não há migration CLI nem roles Supabase confirmadas neste checkout. |
| Schema `bravo_shadow` | Criado em outros rascunhos SQL | O DDL novo pressupõe que possa criar/usar esse schema. |
| Roles Supabase | README do Supabase descreve roles padrão; CI PostgreSQL é vanilla | Antes de executar em Supabase local, confirmar roles; em PostgreSQL vanilla, os `REVOKE` falharão se os papéis nomeados não existirem. |
| RLS | DDL novo habilita RLS sem policies | Falha fechada para roles comuns; não permite runtime até policies/grants revisados. |
| Transições de status | Apenas valores permitidos via CHECK | CHECK não impede transições inválidas entre estados; exige serviço transacional com lock ou trigger revisado. |
| Aprovação | Hash aprovado deve ser igual ao manifesto | O DDL impede hash diferente, mas a autenticação/autoridade do aprovador ainda depende de camada futura. |
| Proveniência | Chave composta de origem e unicidade do destino | A estrutura impede duplicação lógica, mas a gravação atômica junto ao registro funcional ainda não existe. |

## 3. Ajustes e limites identificados

1. A observação no SQL foi corrigida para deixar claro que o bloqueio de produção é uma obrigação do futuro importador; o DDL sozinho não implementa esse gate.
2. O SQL continua como rascunho. Não o adicionar ainda a `supabase/migrations/`.
3. Não criar roles artificiais no schema de produção nem usar `service_role`/superuser como credencial permanente.
4. Para teste em PostgreSQL vanilla, o harness descartável deverá criar explicitamente as roles exigidas ou o DDL de migration deverá usar uma estratégia compatível com o Supabase local sem enfraquecer o REVOKE.
5. O teste de DDL futuro precisa executar a migration em banco vazio e em banco já contendo o schema `bravo_shadow`, verificar constraints, RLS, rollback e comportamento concorrente.
6. A máquina de estados deve validar transições permitidas sob lock. Estados finais não podem voltar a `prepared`; `apply` deve exigir lote aprovado, hash idêntico e ambiente descartável.
7. A transação de importação deverá inserir o registro funcional e a proveniência na mesma conexão/transação. A estrutura atual do backend não fornece ainda esse adaptador.

## 4. Testes estáticos adicionados

Foi adicionado `backend/tests/test_migration_control_schema_draft.py` para verificar:
- exatamente as duas tabelas esperadas;
- chave composta de origem e unicidade do destino;
- vínculo da aprovação ao hash;
- lista restrita de ambientes;
- RLS habilitado e ausência de GRANT/policies permissivas;
- ausência de comandos de inserção/atualização/exclusão de dados.

Esses testes protegem o contrato textual do rascunho. **Não são parser SQL, não executam DDL e não substituem testes PostgreSQL.**

## 5. Próximo gate técnico

1. Inicializar Supabase local isolado, com CLI/Docker, somente em máquina de desenvolvimento autorizada.
2. Gerar migration oficial via `supabase migration new`, após revisão.
3. Executar em banco descartável vazio e verificar constraints/RLS/roles.
4. Testar concorrência de mesma identidade, colisão de destino, hash alterado e rollback atômico.
5. Só depois desenhar o adaptador de persistência, ainda sem acesso a produção.

**Nenhuma migration foi criada/aplicada, nenhum banco foi iniciado e nenhuma credencial foi usada nesta revisão.**


## 6. Identidade do lote e colisão entre versões

A inspeção do manifesto encontrou uma incompatibilidade de modelo: o identificador determinístico do lote era derivado apenas de sistema, baseline e snapshot, enquanto o hash do manifesto também mudava quando a versão do importador ou do mapeamento mudava. Como `migration_batches.batch_id` é chave primária, reprocessar o mesmo snapshot com uma versão diferente poderia colidir com o lote anterior e impedir a trilha auditável.

**Correção aplicada:** `batchId` agora inclui as versões do envelope, formato do manifesto, canonicalização, importador e mapeamento. Testes cobrem mudança de versão do importador e do mapeamento, além da repetibilidade para entradas idênticas. O SQL de controle continua compatível porque mantém `batch_id` como chave primária e não exige alteração de coluna.

Essa mudança é de identidade lógica e não executa importação nem altera dados.


## 7. Máquina de estados pura adicionada

Foi criada `backend/app/core/migration_batch_state.py` com validação fail-closed, sem persistência:
- `prepared → approved → applying → applied → verified`;
- falha pode ser registrada nos estados de execução permitidos;
- rollback somente após aplicação;
- `failed` e `rolled_back` são terminais;
- aprovação exige revisor, data e hash exatamente igual ao manifesto;
- `applying` exige hash do dry-run idêntico ao hash aprovado;
- todos os estados exigem ambiente `local_disposable` ou `ci_ephemeral`.

Os testes em `backend/tests/test_migration_batch_state.py` cobrem fluxo válido, hash divergente, ambiente proibido, rollback prematuro, estados terminais e imutabilidade.

**Limite importante:** isso é regra de domínio em memória. Antes de uso persistente, o adaptador PostgreSQL deverá executar a leitura com `SELECT ... FOR UPDATE`, validar e atualizar o estado dentro da mesma transação. A função pura, sozinha, não oferece bloqueio concorrente nem autorização de usuário.


## 8. Adaptador PostgreSQL com bloqueio de linha

Foi adicionado `backend/app/core/migration_batch_state_postgres.py`. A operação:
1. Abre uma unidade de trabalho somente quando chamada, usando fábrica injetada.
2. Lê o lote com `SELECT ... FOR UPDATE`.
3. Reconstitui e valida a aprovação persistida e seu vínculo com o manifesto.
4. Aplica a máquina de estados pura.
5. Atualiza status e campos de aprovação com condição de compare-and-set (`batch_id + manifest_hash + status anterior`).
6. Confirma tudo pela unidade de trabalho; exceções provocam rollback.

Testes com banco falso cobrem bloqueio, persistência do fluxo, lote ausente, aprovação parcial, hash divergente e compare-and-set.

**Limitações mantidas:** não cria lotes, não autentica nem autoriza o revisor, não executa importação e não inicializa conexão automaticamente. O SQL continua sendo rascunho não aplicado. A autenticação/autoridade do aprovador deve ser verificada pela camada de aplicação antes de chamar o adaptador.
