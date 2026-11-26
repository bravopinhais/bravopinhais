# Desenho do controle de lotes de migração — Bravo Shadow

**Status:** proposta técnica documental; não é migration SQL e não foi aplicada ao banco.  
**Escopo:** controle de importações do legado para o Shadow, com execução local e dados sintéticos até autorização específica.  
**Referência funcional:** `docs/especificacao-importador-migracao-v1.md`.

## 1. Objetivo e separação de responsabilidades

As tabelas de negócio armazenam o estado atual dos módulos do Bravo. As tabelas de controle registram o que foi recebido, planejado, aplicado, verificado ou bloqueado durante cada lote.

O controle não deve:
- substituir os IDs legados;
- guardar cópias integrais de registros pessoais ou documentos quando hashes e referências bastarem;
- transformar uma simulação em autorização de aplicação;
- corrigir automaticamente referências ausentes, ambíguas ou conflitantes;
- permitir que uma repetição do mesmo lote duplique dados;
- servir como mecanismo de autenticação ou conceder permissões de negócio.

## 2. Modelo lógico proposto

Quatro grupos de dados, todos no schema privado `bravo_shadow` quando a implementação for aprovada:

1. `migration_batches`: identidade e estado consolidado de cada lote recebido.
2. `migration_source_map`: identidade de origem associada ao registro de destino, com unicidade por origem.
3. `migration_batch_events`: trilha append-only de execuções, transições e resultados.
4. `migration_decisions`: decisões humanas explícitas para conflitos, órfãos e referências ambíguas.

A separação entre lote e eventos é intencional: um lote pode passar por inspeção, várias simulações e uma aplicação autorizada, sem apagar o histórico das tentativas anteriores.

## 3. Tabela `migration_batches`

Campos propostos:

| Campo | Finalidade |
|---|---|
| `batch_id` | UUID gerado para identificar o lote no Shadow |
| `source_system` | Sistema de origem, por exemplo identificador estável do Bravo legado |
| `source_branch` | Branch/revisão de origem declarada no envelope |
| `source_baseline` | Revisão ou baseline do snapshot |
| `snapshot_hash` | Hash do envelope/snapshot recebido |
| `format_version` | Versão do formato de exportação |
| `importer_version` | Versão do importador |
| `mapping_version` | Versão das regras de mapeamento |
| `environment` | Deve identificar explicitamente ambiente local Shadow |
| `status` | Estado consolidado: recebido, inspecionado, simulado, aprovado, aplicado, verificado, bloqueado ou falhou |
| `record_counts` | Contagens por coleção e resultado, sem payload pessoal |
| `created_at`, `updated_at` | Datas de controle em UTC |
| `approved_by`, `approved_at` | Identidade e instante da aprovação explícita, nulos até aprovação |
| `manifest_hash` | Hash do manifesto final, quando existir |

Restrições propostas:
- `batch_id` como chave primária.
- Não aceitar `apply` se o lote não estiver explicitamente aprovado e com ambiente compatível.
- Unicidade opcional para detectar repetição exata de `source_system + snapshot_hash + mapping_version`; a política deve distinguir reenvio do mesmo lote de uma nova tentativa intencional.
- O estado atual é uma projeção conveniente; a trilha de eventos é a fonte de auditoria das transições.

## 4. Tabela `migration_source_map`

Esta tabela é o registro de identidade entre origem e destino, não uma tabela de negócio.

| Campo | Finalidade |
|---|---|
| `map_id` | UUID técnico |
| `source_system` | Sistema de origem |
| `source_collection` | Coleção/chave do payload legado |
| `legacy_id` | ID original, preservado como texto |
| `destination_schema` | Schema de destino, inicialmente `bravo_shadow` |
| `destination_table` | Tabela de destino |
| `destination_id` | ID efetivamente persistido no destino |
| `source_record_hash` | Hash canônico do registro de origem |
| `first_batch_id` | Lote que criou o vínculo |
| `last_batch_id` | Lote mais recente que avaliou o vínculo |
| `status` | mapeado, aplicado, conflito, órfão, ambíguo ou ignorado com decisão |
| `created_at`, `updated_at` | Datas de controle |

Restrições e comportamento:
- Chave única sobre `(source_system, source_collection, legacy_id)`.
- O ID legado não deve ser convertido em número nem normalizado de forma destrutiva.
- O destino deve guardar o ID preservado sempre que o modelo de negócio permitir.
- Se já existir o ID no destino sem vínculo de origem compatível, classificar como colisão; nunca assumir que é o mesmo registro.
- A mesma identidade de origem não pode apontar para dois destinos ativos.
- A atualização do hash de origem não autoriza sobrescrever o destino: classificar como alteração de origem e exigir regra/decisão explícita.
- Índices adicionais por `(destination_schema, destination_table, destination_id)` para detectar colisões de destino.

## 5. Tabela `migration_batch_events`

Trilha append-only de eventos. Campos propostos:

- `event_id` UUID primário;
- `batch_id` FK para `migration_batches`;
- `execution_id` UUID para agrupar uma execução específica (inspect, dry_run, apply, verify ou rollback);
- `event_type` e `event_status`;
- `occurred_at` em UTC;
- `actor_subject` e `actor_email`, quando houver operador autenticado;
- `request_id`/correlation ID;
- `counts` em JSON estruturado;
- `details` limitado a metadados técnicos, códigos de erro e IDs de origem não sensíveis quando estritamente necessários.

Não registrar tokens, credenciais, conteúdo de documentos, CPF, telefone, e-mail de moradores ou payload bruto nos eventos. Eventos não devem ser editados ou excluídos pela role normal da aplicação. Correções são novos eventos.

## 6. Tabela `migration_decisions`

Registra decisões que não podem ser inferidas com segurança pelo importador:

- `decision_id` UUID;
- `batch_id` e, quando aplicável, `map_id`;
- `source_system`, `source_collection`, `legacy_id`;
- `decision_type`: resolver referência, tratar órfão, resolver ambiguidade, aceitar colisão após análise ou excluir registro do escopo;
- `resolution` estruturada e validada por tipo;
- `rationale` obrigatório;
- `decided_by`, `decided_at`;
- `status`: proposta, aprovada, rejeitada ou revogada;
- `supersedes_decision_id` para substituir uma decisão sem apagar a anterior.

Uma decisão só vale para o lote/identidade e versão de mapeamento a que se refere. Mudança de snapshot ou regra pode exigir nova análise. Não aceitar decisão sem ator, justificativa e escopo explícitos.

## 7. Idempotência, concorrência e transações

- A chave de idempotência de origem é `(source_system, source_collection, legacy_id)`.
- O hash do registro deve usar algoritmo/versionamento documentado e serialização canônica estável.
- A criação do registro de negócio e do vínculo em `migration_source_map` deve ocorrer na mesma transação.
- A aplicação do lote deve reservar/serializar a execução por `batch_id`, evitando duas aplicações concorrentes.
- Usar restrições únicas como última defesa contra duplicidade; não depender apenas de consulta prévia na aplicação.
- Cada unidade transacional deve confirmar dados de negócio, mapa de origem e evento de resultado de forma consistente.
- Falha deve provocar rollback da unidade em andamento; o manifesto/evento de falha deve ser persistido em transação separada depois que a conexão de aplicação for liberada.
- Não presumir transação global para todo o snapshot: aplicar por domínio/unidade definida, com dependências e checkpoints explícitos.
- `verify` compara contagens, IDs, hashes e referências; não altera registros.
- Rollback não deve apagar histórico nem desfazer alterações posteriores. Preferir compensação controlada; restauração destrutiva requer procedimento e aprovação separados.

## 8. RLS, roles e acesso

O DDL de referência atual habilita RLS nas tabelas de negócio e não cria policies permissivas; também revoga grants das roles padrão. Isso é um bloqueio de segurança intencional, não um defeito a contornar.

Antes de criar as tabelas de controle, definir e testar:
- role PostgreSQL dedicada ao backend, sem superuser e sem `BYPASSRLS`;
- role distinta para tarefas de migração, ativada somente no processo local autorizado;
- privilégios mínimos por tabela e operação;
- policies RLS explícitas, coerentes com a identidade autenticada e com o fluxo operacional;
- proteção append-only para eventos e decisões históricas;
- ausência de acesso direto via Data API para `anon` e `authenticated`;
- separação de credenciais entre desenvolvimento, staging e produção.

Não conceder acesso amplo ao schema nem usar a role `service_role` como atalho. O desenho final das policies depende da arquitetura real de conexão e contexto de usuário, ainda não validada.

## 9. Privacidade e retenção

- Guardar hashes, contagens e identificadores técnicos sempre que suficientes.
- Evitar payload bruto nas tabelas de controle.
- Restringir logs e exportações de manifesto; não incluir dados pessoais.
- Definir prazo de retenção para snapshots, arquivos temporários e logs detalhados.
- O manifesto deve ser suficiente para auditoria sem reproduzir dados pessoais.
- Acesso a decisões e trilhas deve ser restrito e auditável.

## 10. Fluxo operacional proposto

1. Receber envelope e validar versão/formato.
2. Criar lote em estado recebido e registrar evento.
3. Inspecionar coleções e presença explícita de cada coleção.
4. Calcular hashes e montar inventário.
5. Executar dry-run; registrar resultados sem escrever nas tabelas de negócio.
6. Bloquear automaticamente colisões, órfãos e ambiguidades não resolvidos.
7. Registrar decisões humanas necessárias.
8. Gerar manifesto imutável e solicitar aprovação explícita.
9. Aplicar apenas em ambiente local Shadow autorizado, com transações por domínio.
10. Verificar IDs, hashes, referências, contagens e reconciliação.
11. Fechar lote como verificado ou falho, mantendo eventos e evidências.

## 11. Questões que permanecem abertas

- Quem poderá aprovar formalmente um lote e qual será o mecanismo de autenticação dessa aprovação?
- A retenção do snapshot bruto será necessária após a geração do inventário?
- A tabela de mapeamento deverá manter histórico de múltiplos destinos antigos após correções, ou apenas o vínculo vigente com eventos de alteração?
- Quais políticas RLS e roles serão compatíveis com o modelo de conexão do backend?
- Qual o prazo de retenção de eventos e decisões?

Essas questões não bloqueiam a documentação, mas bloqueiam a criação de uma migration executável.

## 12. Próxima etapa segura

Revisar este modelo contra os schemas Pydantic e os adaptadores PostgreSQL existentes; em seguida, especificar constraints e testes automatizados com dados sintéticos. Só depois elaborar um SQL separado, ainda não aplicado. A criação e execução da migration local dependem de revisão e autorização explícitas.

**Estado desta entrega:** somente desenho documental. Nenhuma tabela foi criada, nenhuma migration foi aplicada, nenhum dado legado foi importado e nenhuma conexão de produção foi realizada.
