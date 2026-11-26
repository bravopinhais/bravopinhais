# Contrato transacional e tratamento de datas — importador Bravo Shadow

**Status:** especificação técnica documental; não implementada.  
**Branch:** `bravo-shadow`.  
**Ambiente previsto:** somente PostgreSQL local descartável, após revisão e autorização próprias.  
**Não realizado:** alteração de schema, execução de migration, conexão ao banco ou importação.

## 1. Objetivo

Definir o limite transacional do importador para que o registro de negócio, o mapa de identidade da origem e o evento de sucesso sejam confirmados como uma única unidade. Definir também como preservar datas históricas sem conversões ambíguas.

Este contrato complementa:
- `docs/especificacao-importador-migracao-v1.md`;
- `docs/desenho-controle-lotes-migracao.md`;
- `docs/auditoria-compatibilidade-importador.md`.

## 2. Princípios obrigatórios

1. O importador não usa os endpoints comuns de criação quando estes geram IDs ou abrem transações independentes.
2. O ID legado permanece texto opaco, sem conversão numérica ou normalização destrutiva.
3. A gravação de negócio, o vínculo de origem e o evento de sucesso compartilham a mesma conexão e transação PostgreSQL.
4. Uma exceção antes do commit reverte todos os três efeitos.
5. Uma repetição consulta a identidade única da origem e o hash registrado; nunca presume equivalência apenas porque o ID de destino existe.
6. A execução `dry_run` não abre caminho de escrita nem cria registros de controle que possam ser confundidos com aplicação.
7. A role de migração deverá ser dedicada, de privilégio mínimo e sem superuser/BYPASSRLS. A configuração efetiva depende de desenho e testes RLS ainda pendentes.

## 3. Unidade transacional de aplicação

### 3.1 Entrada do serviço

O serviço recebe um comando validado contendo:
- `batch_id`;
- `execution_id`;
- `source_system`;
- `source_collection`;
- `legacy_id` como string;
- `source_record_hash` e versão do algoritmo;
- destino lógico aprovado (schema/tabela);
- payload de destino já validado;
- ator/identidade técnica da execução;
- versão do mapeamento.

O serviço não aceita URL de conexão, credenciais ou nome de ambiente fornecidos pelo payload. A conexão é injetada pela configuração local do processo e deve ser validada fora do importador.

### 3.2 Ordem dentro de uma única conexão

Dentro de uma única transação:
1. bloquear/serializar a execução do lote e a identidade de origem;
2. consultar o mapa por `(source_system, source_collection, legacy_id)`;
3. classificar repetição idêntica, alteração de origem ou colisão;
4. se for um novo registro elegível, inserir o destino com o ID preservado;
5. inserir `migration_source_map` com hash, destino e lote;
6. inserir evento de sucesso `record_applied` e contagens incrementais necessárias;
7. confirmar a transação.

O evento de sucesso não pode ser gravado em conexão separada. O mapa e o destino não podem ter commits independentes.

### 3.3 Comportamento por classificação

| Situação | Ação |
|---|---|
| Sem mapa e sem ID no destino | Elegível para inserção; gravar destino + mapa + evento atomicamente |
| Mapa existente e hash igual | Classificar `already_applied`; não alterar destino |
| Mapa existente e hash diferente | Classificar `conflict_changed_source`; bloquear atualização automática |
| ID já existe no destino sem mapa compatível | Classificar `destination_id_collision`; bloquear |
| Mapa aponta para destino inexistente | Inconsistência de controle; bloquear e exigir reconciliação |
| Referência obrigatória ausente/ambígua | Não aplicar registro; registrar pendência no plano |

Uma classificação sem escrita de negócio pode ser registrada em evento próprio, conforme a política de auditoria. O registro de sucesso de aplicação permanece sempre atômico com o destino e o mapa.

### 3.4 Falhas e recuperação

- Qualquer erro após o início da unidade e antes do commit provoca rollback da conexão.
- Depois do rollback, o orquestrador pode registrar um evento técnico `record_apply_failed` em transação separada. Esse evento deve deixar explícito que a unidade de negócio foi revertida.
- Se a gravação desse evento secundário falhar, a execução deve continuar marcada como incompleta no relatório externo/manifesto local; não se deve repetir a aplicação às cegas.
- Se o commit retornar erro ou resultado incerto por perda de conexão, a próxima tentativa deve consultar o mapa e o destino antes de qualquer nova escrita.
- Restrições únicas no banco são a defesa final contra concorrência. Uma consulta prévia isolada não é garantia de idempotência.
- Não fazer retry automático de erro de integridade, colisão ou validação. Retry técnico limitado só pode ser definido para falhas transitórias identificadas e com consulta de estado após resultado incerto.

## 4. Contrato de conexão e repositórios

O `PostgresUnitOfWork` atual abre uma conexão por contexto e faz commit/rollback/close. Os adaptadores existentes encapsulam chamadas em suas próprias unidades; portanto, não devem ser encadeados para implementar a importação atômica.

A implementação futura deverá escolher uma das opções, após revisão:
- repositórios/commands de importação que recebam explicitamente a mesma conexão/cursor; ou
- um `MigrationUnitOfWork` que exponha conexão e operações de domínio/control dentro de um único contexto.

Não manter duas unidades de trabalho aninhadas para a mesma operação. Não usar chamadas HTTP internas para compor a transação. O contrato deve ser tipado e testável com conexão/cursor falsos, sem banco real.

O fluxo especializado de estoque permanece separado: inserir produto/saldo inicial e importar movimentos exige ordem e reconciliação próprias, respeitando imutabilidade do histórico. Não utilizar CRUD de movimento comum como substituto de importação histórica.

## 5. Datas históricas: representação dual

### 5.1 Problema confirmado

O schema de API de `Acerto` declara `data: str`; a ficha do legado documenta texto pt-BR; o SQL atual declara `data timestamptz not null`; o adaptador envia a string diretamente e serializa leituras como ISO. Essa combinação não garante preservação nem interpretação consistente.

### 5.2 Modelo recomendado

Para histórico importado, separar:

- `data_legada_texto`: texto original exatamente como recebido, sem trim, reformatar, completar ano ou trocar separadores;
- `data_normalizada`: valor temporal opcional, preenchido somente quando a regra de parsing for inequívoca;
- `data_normalizacao_status`: por exemplo `not_attempted`, `normalized`, `ambiguous`, `invalid`;
- `data_normalizacao_rule`: identificador/versionamento da regra aplicada, quando houver;
- `data_fuso_origem`: informação de fuso, quando explicitamente fornecida pela origem; caso contrário nula.

A coluna temporal de consulta e o tipo final (`date` ou `timestamptz`) precisam ser decididos conforme a semântica real dos dados. Não atribuir meia-noite ou fuso presumido a uma data sem hora. Não converter uma data civil para timestamp UTC sem regra aprovada.

A representação original é a referência de preservação. A normalizada é um atributo derivado e descartável/recalculável mediante regra versionada.

### 5.3 Regras de interpretação

1. Guardar primeiro o valor bruto e seu hash.
2. Reconhecer apenas formatos explicitamente documentados e testados.
3. Para data ISO `AAAA-MM-DD`, validar calendário real; não basta regex.
4. Para formato brasileiro, aceitar somente padrões aprovados, por exemplo `DD/MM/AAAA`, com validação de calendário.
5. Valores como `01/02/2024` só podem ser interpretados porque a regra do formato está definida como dia/mês/ano para aquela coleção e baseline; não inferir formato a partir do valor.
6. Datas sem ano, datas com hora sem fuso, strings vazias e valores livres ficam não normalizados até decisão explícita.
7. Datas impossíveis (ex.: `31/02/2024`) recebem status `invalid`; não corrigir para o último dia do mês.
8. Nenhum registro é descartado por data inválida: fica pendente e aparece no relatório de validação.
9. Não sobrescrever o texto original depois de normalizar.
10. Toda regra de parsing tem identificador e versão incluídos no manifesto.

### 5.4 Compatibilidade de API

Não alterar o contrato público de `Acerto.data` inadvertidamente. A implementação deve decidir se:
- mantém `data` como texto legado/API e usa campos internos adicionais; ou
- cria um DTO de migração separado e adapta explicitamente a leitura/escrita.

A decisão exige testes de contrato das rotas atuais. Não retornar timestamp ISO onde consumidores esperam a representação textual histórica sem uma mudança de API aprovada.

## 6. Hash e canonicalização

- Calcular `source_record_hash` sobre o registro bruto e preservar o snapshot original.
- Versionar algoritmo e canonicalização.
- Não converter decimal por `float`; usar texto decimal/Decimal.
- Não normalizar datas, strings, zeros à esquerda, IDs, Base64 ou Unicode de forma destrutiva para o hash da origem.
- Se for necessário hash derivado do registro mapeado, armazená-lo separadamente do hash bruto da origem.
- Alteração no algoritmo exige nova versão, não reinterpretação silenciosa de hashes existentes.

## 7. Testes sintéticos obrigatórios

### Transação/idempotência
- sucesso grava destino, mapa e evento na mesma conexão;
- falha após inserir destino reverte destino, mapa e evento;
- falha após inserir mapa reverte os três;
- falha ao inserir evento de sucesso reverte destino e mapa;
- repetição do mesmo ID/hash retorna `already_applied` sem duplicar;
- mesmo ID com hash diferente bloqueia;
- colisão de ID sem mapa bloqueia;
- duas execuções concorrentes não criam duplicidade;
- commit com resultado incerto força consulta de estado antes de retry.

### Datas
- `25/11/2021` interpretada apenas sob regra pt-BR aprovada;
- `2021-11-25` validada como ISO;
- `31/02/2024` inválida e preservada como texto;
- string vazia preservada e não normalizada;
- data sem ano não inferida;
- timestamp sem fuso não recebe UTC arbitrariamente;
- o texto original permanece idêntico após normalização;
- resposta da API mantém o contrato existente.

### Dados complementares
- Decimal de limite e escala inválida;
- referência órfã/ambígua;
- Gzip/Base64 corrompido;
- reconciliação de saldo inicial + entradas − saídas;
- movimento histórico que contraria regra operacional atual não é corrigido silenciosamente.

Os testes deverão usar fixtures sintéticas e doubles de conexão/cursor. Nenhuma conexão PostgreSQL é necessária para a primeira bateria unitária.

## 8. Critérios de aceite

- [ ] Uma única conexão é usada para destino, mapa e evento de sucesso.
- [ ] Falha em qualquer gravação provoca rollback integral da unidade.
- [ ] A repetição é idempotente e protegida por constraints.
- [ ] Colisões e alterações de origem nunca sobrescrevem automaticamente.
- [ ] Datas originais são preservadas byte/textualmente no campo apropriado.
- [ ] Normalização é opcional, versionada e sem fuso presumido.
- [ ] Contrato público da API é preservado ou alterado com testes e aprovação.
- [ ] RLS/roles e migrations locais foram revisados antes de qualquer execução.
- [ ] Testes sintéticos passam antes de conectar ao PostgreSQL local.

## 9. Próxima etapa

Implementar somente os testes unitários sintéticos do contrato e um parser puro de datas com regras explícitas, sem conexão com banco. Depois revisar os resultados e o contrato de API. A criação de SQL/migration permanece bloqueada até resolver RLS, roles e aprovação específica.

**Conclusão:** o importador deverá operar como um serviço transacional próprio, não como uma sequência de CRUDs existentes. O texto histórico da data deve ser preservado independentemente de qualquer interpretação temporal.
