# Revisão técnica da persistência do controle de migração

**Status:** especificação documental revisada; não é SQL executável.  
**Branch:** `bravo-shadow`.  
**Limites:** nenhuma tabela criada, nenhuma migration aplicada, nenhuma conexão PostgreSQL aberta e nenhum dado real utilizado.

## 1. Resultado da revisão

O desenho inicial de quatro tabelas é uma boa separação conceitual, mas precisa de ajustes antes de virar DDL:

1. O identificador de lote produzido pelo manifesto atual não é UUID. É a chave determinística `batch-<sha256>`. O banco não deve tentar armazená-la em uma coluna UUID.
2. A revisão humana agora tem histórico versionado em memória. Uma única linha mutável por decisão não preservaria esse histórico; é necessária uma tabela de eventos de revisão append-only.
3. O ledger de revisão é vinculado ao `batch_id` e ao `manifest_hash`. A persistência deve manter ambos e rejeitar associação a outro manifesto.
4. O mapa de origem deve impedir duplicidade por identidade legada e também concorrência de duas aplicações.
5. O estado consolidado do lote deve ser uma projeção; eventos históricos não podem ser atualizados ou apagados pela role normal da aplicação.

## 2. Identidade do lote: compatibilidade com o manifesto

O código atual cria `batch_id = "batch-" + sha256(canonical_identity)`. A chave é estável para a mesma combinação de sistema, baseline e snapshot.

Modelo recomendado:
- `batch_pk uuid primary key`: chave técnica interna do PostgreSQL;
- `batch_key text not null unique`: recebe exatamente o `manifest.batch_id` atual;
- `manifest_hash text`: hash do manifesto específico;
- `snapshot_hash text`: hash do snapshot de origem.

Não converter a chave determinística em UUID nem truncar o hash. A chave técnica interna nunca substitui a identidade de lote do manifesto.

A mesma identidade de lote pode ser reavaliada com versões diferentes de importador/mapeamento, mas isso deve gerar nova versão de manifesto e novo evento, sem sobrescrever a evidência anterior. A política de reabertura/reexecução deve ser definida antes do DDL final.

## 3. Modelo lógico revisado

### 3.1 `migration_batches`

Responsabilidade: catálogo/projeção do lote.

Campos mínimos propostos:
- `batch_pk uuid primary key`;
- `batch_key text not null unique`;
- `source_system text not null`;
- `source_branch text not null`;
- `source_baseline text not null`;
- `snapshot_hash text not null`;
- `manifest_hash text`;
- `format_version integer not null`;
- `importer_version text not null`;
- `mapping_version text not null`;
- `environment text not null check (environment = 'shadow-local')`;
- `status text not null`;
- `created_at timestamptz not null`;
- `updated_at timestamptz not null`;
- `approved_by text`, `approved_at timestamptz`.

Restrições:
- aprovação exige ator e data juntos; ambos nulos antes da aprovação;
- `apply` não pode depender apenas do campo `status`: deve verificar aprovação, ambiente, hash do manifesto e ausência de bloqueios;
- a transição de estado deve gerar evento na mesma transação;
- o estado deve ser atualizado por serviço transacional único, não por endpoint CRUD genérico.

### 3.2 `migration_source_map`

Responsabilidade: idempotência e rastreio de identidade.

Campos mínimos:
- `map_id uuid primary key`;
- `source_system text not null`;
- `source_collection text not null`;
- `legacy_id text not null`;
- `destination_schema text not null`;
- `destination_table text not null`;
- `destination_id text not null`;
- `source_record_hash text not null`;
- `first_batch_pk uuid not null references migration_batches(batch_pk)`;
- `last_batch_pk uuid not null references migration_batches(batch_pk)`;
- `status text not null`;
- `created_at/updated_at timestamptz not null`.

Constraints e índices:
- UNIQUE `(source_system, source_collection, legacy_id)`;
- índice em `(destination_schema, destination_table, destination_id)`;
- índice em `(first_batch_pk)` e `(last_batch_pk)`;
- validar colisão de destino dentro da transação; a tabela não pode assumir que um ID de destino é exclusivo globalmente entre todas as tabelas;
- preservar `legacy_id` como texto opaco, sem trim, conversão numérica ou alteração de caixa.

O vínculo atual não deve ser sobrescrito quando o hash muda. A tentativa vira conflito e gera evento. Se for necessário corrigir um mapeamento, manter histórico por eventos ou uma tabela de versões; não apagar a trilha anterior.

### 3.3 `migration_batch_events`

Responsabilidade: eventos de execução e transições append-only.

Campos mínimos:
- `event_id uuid primary key`;
- `batch_pk uuid not null references migration_batches(batch_pk)`;
- `execution_id uuid not null`;
- `event_type text not null`;
- `event_status text not null`;
- `occurred_at timestamptz not null`;
- `actor_subject text`;
- `actor_email text`;
- `request_id text`;
- `counts jsonb not null default '{}'`;
- `details jsonb not null default '{}'`.

A role da API não recebe UPDATE/DELETE. Corrigir um evento significa acrescentar outro evento. Não gravar tokens, payload bruto, CPF, telefone, e-mail/endereço de moradores, conteúdo de documentos ou Base64.

### 3.4 `migration_decisions` e `migration_decision_events`

Separar a identidade da pendência de seu histórico de revisão.

`migration_decisions`:
- `decision_pk uuid primary key`;
- `batch_pk uuid not null references migration_batches(batch_pk)`;
- `decision_key text not null` (chave estável emitida pelo registro de decisões);
- `manifest_hash text not null`;
- `decision_type text not null`;
- `source_system/source_collection/legacy_id text`;
- `issue_code text`;
- `created_at timestamptz not null`;
- UNIQUE `(batch_pk, decision_key)`.

`migration_decision_events`:
- `event_id uuid primary key`;
- `decision_pk uuid not null references migration_decisions(decision_pk)`;
- `version integer not null check (version > 0)`;
- `reviewer_id text not null`;
- `choice text not null check (...)`;
- `rationale text not null check (length(trim(rationale)) > 0)`;
- `reviewed_at timestamptz not null`;
- UNIQUE `(decision_pk, version)`.

A escrita deve bloquear a linha da decisão (`SELECT ... FOR UPDATE`) ou usar controle otimista equivalente. A versão esperada precisa coincidir com a última versão persistida. A gravação é INSERT-only; proibir UPDATE/DELETE na tabela de eventos para a role operacional.

A escolha `approved_for_manual_resolution` significa somente que uma pessoa autorizou uma análise/resolução manual posterior. Não equivale a autorização de importação e não remove bloqueios do plano.

## 4. Contrato transacional

Para cada unidade de domínio aprovada:
1. iniciar uma única conexão/transação;
2. bloquear/reservar o lote para impedir execução concorrente;
3. conferir `batch_key`, `manifest_hash`, ambiente local e aprovação;
4. conferir pendências e decisões humanas aplicáveis;
5. gravar o registro de negócio;
6. gravar `migration_source_map`;
7. gravar evento de sucesso;
8. confirmar a transação.

Se qualquer etapa falhar, rollback integral da unidade. Evento de falha pode ser gravado em transação separada depois de liberar a conexão que falhou. Não afirmar sucesso quando o resultado do commit for incerto: consultar o estado usando a chave de idempotência antes de repetir.

As rotas e repositórios CRUD atuais não devem ser encadeados se cada um abrir sua própria transação. O importador precisa de repositório especializado que receba a conexão compartilhada.

## 5. Segurança e RLS: bloqueios que permanecem

O SQL financeiro atual habilita RLS e revoga grants das roles padrão, sem policies permissivas. Isso é uma barreira deliberada.

Antes de DDL de controle, ainda é obrigatório:
- definir role PostgreSQL dedicada ao backend, sem superuser e sem `BYPASSRLS`;
- definir role separada e temporária para execução local do importador;
- conceder somente operações e tabelas necessárias;
- desenhar policies RLS para o modelo real de conexão;
- confirmar que o backend não usa `service_role` como atalho;
- testar negação por padrão e isolamento entre ambientes.

Não adicionar grants genéricos para fazer o piloto funcionar. Não criar policies permissivas sem conhecer a identidade e o contexto transacional efetivamente enviados pelo backend.

## 6. Testes de persistência exigidos antes de qualquer carga

### Restrições
- mesma identidade de origem inserida duas vezes é rejeitada;
- mesmo destino conflitante é bloqueado;
- `batch_key` determinística preserva o valor completo;
- versão repetida de decisão é rejeitada;
- evento histórico não pode ser atualizado ou excluído pela role operacional.

### Atomicidade
- falha ao inserir destino não cria mapa/evento;
- falha ao inserir mapa reverte destino;
- falha ao inserir evento reverte destino e mapa;
- duas aplicações concorrentes do mesmo lote não duplicam;
- retry após commit de resultado incerto consulta a identidade antes de tentar inserir novamente.

### Revisão humana
- ledger de outro manifesto não é aceito;
- versão desatualizada não é aceita;
- decisão sem revisor/justificativa não é aceita;
- revisão não altera o plano nem executa importação;
- eventos anteriores permanecem legíveis após nova revisão.

### Segurança
- roles sem grants não conseguem ler/escrever;
- role da API não pode apagar eventos;
- role de importação não consegue acessar schemas/ambientes não autorizados;
- ausência de policy não é contornada por privilégios elevados.

## 7. Decisões pendentes que bloqueiam DDL final

1. Nome e atributos da role dedicada do backend.
2. Modelo exato de RLS com a conexão atual do FastAPI.
3. Quem pode aprovar um lote e como essa aprovação é autenticada.
4. Retenção do snapshot e dos arquivos temporários.
5. Política de reexecução de um mesmo `batch_key` com versão de mapeamento diferente.
6. Se o histórico do source map será por eventos ou por tabela de versões.

## 8. Próxima etapa segura

Implementar testes unitários sintéticos do contrato transacional com conexão/cursor falso e revisar o desenho de roles/RLS em ambiente local descartável. Só depois preparar DDL isolado para revisão. Esta especificação não autoriza criação de tabela, migration, conexão remota, importação ou cutover.

**Confirmação de segurança:** o Bravo original e seu `index.html` não foram alterados nesta etapa.
