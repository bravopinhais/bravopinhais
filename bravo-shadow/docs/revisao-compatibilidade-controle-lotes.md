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


## 9. Proveniência imutável de registros de origem

Foi criado `backend/app/core/migration_source_records_postgres.py`, que recebe a conexão da unidade de trabalho já aberta e:
- insere a identidade de origem, coleção de destino, ID de destino e hash do registro;
- em repetição, bloqueia a linha existente com `FOR UPDATE`;
- aceita repetição somente se hash e destino forem idênticos;
- preserva o `first_batch_id` original;
- rejeita alteração de conteúdo ou tentativa de redirecionar a mesma identidade para outro destino.

O adaptador não armazena payload, não abre conexão e não faz commit. Deve ser chamado como `write_source_map` dentro de `execute_migration_write_unit`, junto com a gravação funcional e o evento de sucesso. Assim, se qualquer etapa falhar, a unidade de trabalho reverte tudo.

Testes adicionados para repetição idempotente, mudança de hash, redirecionamento de destino e campos/hash inválidos.

**Ainda não há integração com tabelas funcionais específicas.** O adaptador é genérico e depende do chamador fornecer o ID de destino já criado na mesma transação. Nenhum SQL de modelagem foi aplicado.


## 10. Reconciliação de origem e Shadow (somente leitura)

Foi adicionado `backend/app/core/migration_reconciliation.py`, uma comparação pura entre dois conjuntos fornecidos pelo chamador: inventário de origem e vínculos de proveniência do Shadow.

O relatório identifica:
- registro de origem sem vínculo;
- divergência entre hash atual e hash registrado;
- identidade repetida no inventário ou na proveniência;
- destino associado a mais de uma origem;
- vínculo no Shadow ausente do inventário de origem;
- correspondências exatas um-para-um.

A reconciliação não consulta banco, não corrige divergências, não cria vínculos e não autoriza lote. Qualquer divergência torna o relatório inválido; a resolução permanece manual e deve gerar nova evidência/dry-run. O resultado é determinístico para as mesmas entradas.

Testes adicionados com cenários sintéticos de correspondência, ausência, hash divergente, vínculo órfão, duplicidade e repetibilidade.

**Limite atual:** a camada de leitura que coleta snapshots reais ainda não foi implementada. O reconciliador recebe estruturas em memória, mantendo a fronteira de segurança e sem abrir conexão com o banco.


## 11. Leitura controlada do inventário de proveniência

Foi adicionado `backend/app/core/migration_provenance_snapshot_postgres.py`, um leitor que:
- recebe uma conexão já aberta pela camada chamadora;
- exige `SET TRANSACTION READ ONLY` como primeiro comando da transação;
- consulta somente identidade, hash e destino na tabela de proveniência;
- ordena o resultado por sistema, coleção e ID de origem para produzir snapshot determinístico;
- valida cada linha antes de convertê-la em `DestinationProvenance`;
- não lê payloads funcionais, não abre conexão, não confirma nem reverte a transação.

Testes com conexão/cursor falsos cobrem a ordem da transação somente leitura, snapshot vazio, falha de consulta e linha malformada.

**Limites:** o chamador deve fornecer uma conexão em transação ainda sem comandos anteriores, pois PostgreSQL exige que `SET TRANSACTION READ ONLY` seja executado antes da primeira consulta. O leitor não coleta o snapshot do sistema legado nem compara dados funcionais; entrega somente o inventário de proveniência do Shadow ao reconciliador. Nenhuma conexão foi aberta nesta implementação e nenhum SQL foi aplicado.


## Serviço de reconciliação somente leitura

Foi adicionada a camada `backend/app/core/migration_reconciliation_service.py`.
Ela recebe o inventário de origem como tupla imutável fornecida pelo chamador,
solicita ao leitor PostgreSQL o snapshot de proveniência e encaminha ambos ao
comparador puro em memória.

Limites preservados:
- não existe conexão automática com o sistema legado;
- o inventário de origem ainda precisa ser obtido por um processo autorizado e
  fornecido explicitamente ao serviço;
- a conexão PostgreSQL e o ciclo da transação pertencem ao chamador;
- a primeira instrução executada pelo leitor continua sendo
  `SET TRANSACTION READ ONLY`;
- o serviço não grava, corrige, confirma, reverte ou autoriza importações;
- os testes usam conexão/cursor falsos e dados sintéticos; não conectam banco.

Este serviço fecha a orquestração técnica da comparação, mas não representa
validação de dados reais nem conclusão da migração.


## Contrato do snapshot de origem

Foi definido `backend/app/core/migration_source_snapshot.py` como contrato estrutural para uma futura fonte de inventário legado. O objeto imutável `SourceSnapshot` exige sistema de origem, baseline, hash SHA-256 do snapshot, data de exportação e uma tupla de registros com hashes individuais.

O protocolo `SourceSnapshotProvider` descreve a interface esperada de um provedor futuro, mas **nenhum conector concreto foi criado**. O contrato valida que todos os registros pertencem ao sistema declarado e rejeita listas mutáveis, hashes inválidos e itens de tipo incorreto.

Testes sintéticos cobrem metadados ausentes, hash inválido, inventário mutável e mistura de sistemas de origem. Não há leitura de arquivos, APIs ou banco legado; o payload funcional não é carregado por esta abstração.


### Integridade verificável do snapshot

O contrato agora calcula SHA-256 sobre uma representação canônica do inventário: sistema de origem e lista ordenada de identidade (sistema, coleção, ID legado) mais hash individual de cada registro. A ordem de chegada dos registros não altera o hash. A construção de `SourceSnapshot` rejeita um hash que não corresponda ao conteúdo recebido. Isso verifica a integridade do inventário de identidades e hashes, não autentica por si só a origem nem substitui assinatura/cadeia de custódia da exportação.
