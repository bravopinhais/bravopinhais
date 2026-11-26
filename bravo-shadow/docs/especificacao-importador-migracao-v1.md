# Especificação do importador de migração — versão 1

**Branch:** `bravo-shadow`  
**Status:** especificação técnica para revisão; não implementada.  
**Escopo:** importação controlada de coleções do legado para o banco local descartável do Shadow.  
**Fora de escopo:** conexão à produção, extração de dados reais, execução de carga, cutover ou alteração do Bravo original.

## 1. Objetivos e invariantes

O importador deverá permitir ensaios repetíveis, auditáveis e reversíveis sem depender dos endpoints comuns de cadastro.

Invariantes obrigatórios:

1. Preservar o identificador legado como chave de origem e, quando aprovado pelo mapeamento, como ID do registro Shadow.
2. Não gerar um novo ID em reexecuções do mesmo lote.
3. Não sobrescrever silenciosamente registros Shadow preexistentes.
4. Não descartar registros inválidos, órfãos ou ambíguos; isolá-los em relatório de pendências.
5. Preservar valores originais, inclusive strings, zeros à esquerda, pontuação, datas textuais e Base64 Gzip.
6. Nunca tratar `DEFAULT_DATA`, fallback de interface ou dados demonstrativos como origem produtiva.
7. Operar somente em ambiente local descartável até haver autorização específica e gates de segurança aprovados.
8. Não realizar escrita dupla entre o legado e o Shadow.

## 2. Modos de execução

| Modo | Comportamento | Escrita no destino |
|---|---|---|
| `inspect` | Lê um arquivo de entrada previamente obtido por processo autorizado, identifica coleções, campos, IDs e contagens | Não |
| `dry_run` | Executa validações, resolução de referências e plano de operações sem persistir | Não |
| `apply` | Aplica um lote aprovado em banco local descartável, em transação por domínio/lote | Sim |
| `verify` | Compara origem, manifesto e destino; calcula contagens, hashes e divergências | Não |
| `rollback` | Reverte o lote identificado, apenas se o mecanismo transacional e o registro de lote comprovarem que os dados pertencem exclusivamente àquela execução | Sim, controlada |

O modo padrão deve ser `dry_run`. O modo `apply` exige confirmação explícita do operador, identificação do ambiente como local/teste e aprovação do relatório do mesmo hash de lote. Nenhum modo deve aceitar uma URL ou credencial de banco de produção.

## 3. Contrato do lote de entrada

O importador recebe um snapshot de arquivo, nunca uma conexão direta com o sistema legado.

Envelope lógico recomendado:

| Campo | Obrigatório | Regra |
|---|---|---|
| `formatVersion` | Sim | Versão do formato do envelope |
| `sourceSystem` | Sim | Identificador textual do sistema de origem |
| `sourceBranch` | Sim | Referência da versão de código usada para interpretar o formato |
| `sourceBaseline` | Sim | SHA da baseline do legado |
| `exportedAt` | Sim | Data/hora ISO com fuso, gerada pelo processo de exportação |
| `collections` | Sim | Objeto com coleções explicitamente presentes |
| `collectionPresence` | Sim | Para cada coleção: `present`, `missing` ou `unknown` |
| `snapshotHash` | Sim | Hash do arquivo/envelope original, calculado antes da transformação |

Regras:
- Coleção ausente não é equivalente a coleção vazia.
- Cada registro deve manter o objeto bruto original disponível para comparação.
- Campos desconhecidos devem ser preservados no arquivo de origem e reportados; não devem ser descartados sem decisão de mapeamento.
- A exportação não deve incluir segredos, tokens, credenciais ou dados fora do escopo.
- Dados pessoais só poderão entrar em ensaios por meio de conjunto sintético ou anonimizado, com autorização e controles apropriados.

## 4. Identidade, chave e idempotência

Cada registro importado deve ter uma identidade de origem composta por:

`(sourceSystem, sourceCollection, legacyId)`

Regras:
1. `legacyId` é tratado como texto opaco. Não converter para número, não remover prefixos, não alterar maiúsculas/minúsculas.
2. A identidade de origem deve ter restrição única no registro de controle da migração.
3. O destino mantém o ID legado quando não houver colisão e quando o tipo/contrato permitir.
4. Se o ID já existir no destino:
   - se houver vínculo de origem e o hash de conteúdo for igual, classificar como `already_applied`;
   - se houver vínculo de origem e o hash for diferente, classificar como `conflict_changed_source`;
   - se não houver vínculo de origem, classificar como `destination_id_collision`.
5. Não atualizar um registro em colisão automaticamente. Exigir resolução explícita e documentada.
6. Reexecutar o mesmo lote deve produzir o mesmo plano e não duplicar dados.
7. A ordem de registros no arquivo não deve alterar o resultado.

O hash por registro deve ser calculado sobre uma representação canônica e versionada do conteúdo de origem. A canonicalização não pode normalizar valores de negócio. A versão do algoritmo e os campos incluídos no hash devem constar no manifesto.

## 5. Manifesto e rastreabilidade

Cada execução deve criar um manifesto imutável contendo:

- `batchId` único;
- hash do snapshot;
- versão do importador e do mapeamento;
- ambiente/destino identificado como local;
- modo executado;
- data/hora de início e fim;
- coleções incluídas;
- contagens lidas, válidas, rejeitadas, ignoradas e aplicadas;
- hash por coleção e, quando viável, por registro;
- IDs preservados;
- referências resolvidas, órfãs e ambíguas;
- erros e decisões manuais vinculadas;
- resultado final e responsável pela aprovação.

Logs não devem conter conteúdo de documentos, Base64, CPF, telefone, e-mail, endereço ou outros dados pessoais. Para correlação, usar IDs e hashes; limitar acesso ao manifesto detalhado.

## 6. Pipeline de processamento

1. **Validar envelope:** versão, baseline, hash, presença das coleções e formato.
2. **Inventariar:** contar registros e campos, verificar IDs ausentes/duplicados e tipos inesperados.
3. **Validar sem transformar:** verificar campos obrigatórios, formatos e limites conforme cada ficha técnica.
4. **Construir plano:** classificar cada registro como válido, já aplicado, conflito, inválido ou pendente de referência.
5. **Resolver dependências:** executar coleções na ordem aprovada; não criar referências aproximadas.
6. **Apresentar dry-run:** exibir contagens, amostras mascaradas, conflitos e impacto previsto.
7. **Aplicar:** gravar por domínio/lote com transação e controle de origem.
8. **Verificar:** comparar contagens, IDs, hashes e relacionamentos.
9. **Fechar lote:** registrar manifesto final e impedir alteração silenciosa do relatório.

Falha em validação estrutural do envelope interrompe o lote inteiro. Falha em registro individual pode ser isolada no dry-run; no apply, a política padrão é abortar a transação do domínio se a integridade referencial ou a consistência do lote for comprometida.

## 7. Estratégia de persistência e rollback

- Cada domínio deve ser aplicado em transação própria, respeitando dependências.
- O registro de controle do lote e os registros do domínio precisam ser gravados na mesma transação sempre que possível.
- O importador deve registrar quais IDs foram criados por aquele lote.
- Rollback só pode remover registros criados pelo lote quando não houver dependências posteriores nem alterações feitas após a importação.
- Se houver dependências, alteração posterior ou incerteza de propriedade, interromper rollback automático e exigir restauração do snapshot local descartável.
- Não usar exclusão em cascata como atalho.
- A restauração de backup local deve ser ensaiada antes de aceitar o primeiro lote.

## 8. Mapeamento inicial por domínio

| Domínio | Chave de origem | Regra principal | Referências |
|---|---|---|---|
| Condomínio | `id`/registro principal | Preservar todos os campos existentes, inclusive os não exibidos na tela | Nenhuma relação de coleção confirmada |
| Conselho | `id` | Preservar `BlocoAp` exatamente | Relação institucional a confirmar |
| Categorias | `id` | Preservar `id` e `nome` | Documentos por texto legado |
| Motivos de Acerto | `id` | Preservar `id` e `nome`; excluir defaults não comprovados | Acertos por texto legado |
| Fornecedores | `id` | Preservar CNPJ e razão social como texto | Relações adicionais a confirmar |
| Empregados | `id` | Preservar todos os campos textuais | Relações adicionais a confirmar |
| Moradores | `id` | Preservar CPF/telefone/unidade como texto | Relações adicionais a confirmar |
| Plano de Contas | `id` | Preservar código como texto | Financeiro por `planoContaId` |
| Formas Monetárias | `id` | Preservar `multaPct` sem arredondamento silencioso | Uso operacional a confirmar |
| Contas Bancárias | `id` | Preservar saldo decimal; não interpretar como extrato | Nenhuma associação financeira confirmada |
| Financeiro | `id` | Preservar valor decimal e histórico | `planoContaId` opcional |
| Estoque | `id` | Preservar saldo, limites, etiqueta e Gzip | Acertos por `produtoId` |
| Documentos | `id` | Preservar pasta textual, nome e Gzip | Categoria opcional somente por correspondência exata e única |
| Acertos de Estoque | `id` | Preservar data textual, tipo, quantidade e motivo textual | Produto por `produtoId`; motivo textual |
| Dashboard / DRE | Não importar como coleção-base | Reconstruir após módulos de origem aceitos | Financeiro e Plano de Contas |

Este mapa é inicial e deve ser confrontado com o payload sintético de teste e os contratos atuais antes da implementação.

## 9. Validações específicas obrigatórias

### Referências
- Plano de Contas: títulos com `planoContaId` inexistente vão para relatório de órfãos; não inventar conta.
- Documentos: `pasta` permanece textual; associar categoria apenas com uma correspondência exata e única.
- Acertos: preservar `produtoId` mesmo quando órfão no relatório de origem; definir estratégia de armazenamento sem descartar o histórico. Associar `motivoId` apenas se houver correspondência exata e única.
- Categorias e Motivos: distinguir coleção ausente, vazia e valores inseridos por fallback.

### Valores e datas
- Decimais devem ser convertidos sem passagem por ponto flutuante binário; manter escala e valor.
- Datas legadas textuais devem ser armazenadas como origem bruta; conversão temporal só com formato e fuso comprovados.
- CPF, CNPJ, telefone, CEP, códigos e identificadores permanecem strings.
- Campos extras e ausentes devem aparecer no relatório de equivalência.

### Arquivos
- Validar Base64 e descompressão em memória limitada.
- Calcular hash dos bytes descompactados e tamanho antes/depois.
- Preservar Base64 original e nome original; não recompactar.
- Arquivo inválido deve ser isolado com referência ao registro e erro, nunca substituído por arquivo vazio.
- Não gravar conteúdo binário nos logs ou relatórios.

### Estoque
- Registrar saldo importado como saldo de abertura no contexto da migração.
- Não reproduzir exclusões históricas de acertos.
- Comparar saldo final importado com saldo atual do legado e, quando houver histórico completo comprovado, com abertura + entradas − saídas.
- Divergência não explicada bloqueia aceite do domínio.

## 10. Critérios de aceite do importador

- [ ] Testes de idempotência com reexecução do mesmo lote.
- [ ] Testes de colisão de ID e alteração de conteúdo na origem.
- [ ] Testes de IDs duplicados e ausentes.
- [ ] Testes de referências válidas, órfãs e ambíguas.
- [ ] Testes de decimais, strings com zeros à esquerda e datas locais.
- [ ] Testes de arquivos Gzip válidos, inválidos e grandes.
- [ ] Testes de falha transacional e rollback/restauração.
- [ ] Verificação de que dry-run não executa escrita.
- [ ] Verificação de que o importador recusa destino não local/não autorizado.
- [ ] Relatório reproduzível com hashes, contagens e divergências.
- [ ] Execução dos testes com evidência registrada.

## 11. Bloqueios explícitos

A especificação não significa que o importador esteja implementado ou testado. Permanecem bloqueados:
- obter dados reais do legado;
- conectar qualquer ferramenta do Shadow à produção;
- executar `apply` sobre dados reais;
- aplicar migrations em banco hospedado;
- liberar rotas de negócio publicamente;
- cortar ou redirecionar módulos do Bravo original.

**Próxima etapa técnica:** revisar o schema PostgreSQL local e desenhar a tabela de controle de lotes/origem, sem aplicar migrations. Em seguida, criar testes unitários do planejador de importação com dados sintéticos.


## 12. Modelo lógico do controle de lotes e da origem

**Status:** desenho lógico para revisão; não é migration SQL e não foi aplicado a nenhum banco.

O controle é separado dos dados funcionais do Bravo. Ele registra a proveniência e o estado do processamento sem copiar o payload de origem.

### 12.1. Entidade `migration_batches`

| Campo lógico | Tipo recomendado | Regra |
|---|---|---|
| `batch_id` | texto/UUID determinístico | Chave primária lógica; derivada da identidade do snapshot conforme versão do manifesto. |
| `snapshot_hash` | texto SHA-256 | Obrigatório; identifica os bytes/envelope de origem. |
| `manifest_hash` | texto SHA-256 | Obrigatório; vincula o lote ao manifesto aprovado. |
| `source_system` | texto | Obrigatório; parte da identidade de origem. |
| `source_baseline` | texto | SHA da baseline interpretada. |
| `environment` | texto com CHECK | Somente `local_disposable` ou `ci_ephemeral` na V1. Valores de produção são recusados. |
| `mode` | texto com CHECK | `inspect`, `dry_run`, `apply`, `verify` ou `rollback`. |
| `status` | texto com CHECK | `prepared`, `approved`, `applying`, `applied`, `verified`, `failed`, `rolled_back`. |
| `mapping_version` | texto | Versão imutável do mapeamento usado. |
| `created_at`, `finished_at` | timestamp com fuso | Datas de auditoria; não substituem `exportedAt`. |
| `approved_by`, `approved_at` | texto/timestamp com fuso, anuláveis | Preenchidos somente por aprovação explícita, autenticada e vinculada ao hash. |

Restrições:
- `batch_id` é único.
- `manifest_hash` e `snapshot_hash` devem ter formato SHA-256 validado pela aplicação e, quando possível, por CHECK no banco.
- Transições de status são controladas; lote `applied` ou `verified` não pode voltar a `prepared`.
- Um lote aprovado só pode ser aplicado se o hash do manifesto apresentado for idêntico ao hash aprovado.
- A V1 não aceita `environment` de produção, nem mesmo se o operador tentar marcar o lote como aprovado.

### 12.2. Entidade `migration_source_records`

| Campo lógico | Tipo recomendado | Regra |
|---|---|---|
| `source_system` | texto | Não vazio; sem normalização silenciosa. |
| `source_collection` | texto | Nome exato da coleção de origem. |
| `legacy_id` | texto | ID opaco; preservar zeros, prefixos e caixa. |
| `destination_collection` | texto | Coleção/tabela Shadow aprovada no mapeamento. |
| `destination_id` | texto | ID efetivamente atribuído; preservar o legado quando permitido. |
| `source_record_hash` | texto SHA-256 | Hash canônico e versionado do registro de origem. |
| `first_batch_id` | texto/UUID | Lote que criou o vínculo de proveniência. |
| `last_verified_batch_id` | texto/UUID, anulável | Último lote em que conteúdo e vínculo foram verificados. |
| `created_at`, `updated_at` | timestamp com fuso | Auditoria do vínculo, não do dado de negócio. |

Restrições e comportamento:
- Chave única composta: `(source_system, source_collection, legacy_id)`.
- A identidade da origem nunca é atualizada para apontar silenciosamente a outro destino.
- `destination_collection, destination_id` também deve ter unicidade dentro do escopo de destino, impedindo que duas identidades de origem reivindiquem o mesmo registro.
- Alteração do hash de origem gera conflito para revisão; não atualiza automaticamente `source_record_hash`.
- `first_batch_id` referencia o lote criador e não muda em reexecuções.
- A tabela não deve armazenar payload bruto, documentos, Base64, CPF, telefone, e-mail ou endereço.
- A exclusão de um registro funcional não apaga o vínculo de proveniência; deve gerar estado explícito de destino ausente/conflito, sujeito a revisão.

### 12.3. Histórico append-only de decisões

As decisões manuais ficam em registro separado e append-only, vinculadas a:
- identidade de origem;
- hash de origem observado;
- hash do manifesto/lote;
- classificação anterior e decisão escolhida;
- justificativa obrigatória;
- revisor autenticado e instante com fuso.

Uma decisão não altera o manifesto original. Uma nova entrada de decisão gera nova versão de revisão e exige novo dry-run; decisões antigas permanecem auditáveis. A revisão não concede por si só permissão de escrita no banco.

### 12.4. Transação e concorrência

1. Adquirir lock transacional pela identidade composta antes de consultar/inserir o vínculo de origem.
2. Revalidar colisão no destino dentro da mesma transação.
3. Inserir o registro funcional e o vínculo `migration_source_records` na mesma transação.
4. Atualizar contadores/estado do lote na mesma transação do domínio, sempre que possível.
5. Se a restrição única disparar, reler e classificar como reexecução ou conflito; nunca repetir INSERT sem classificação.
6. Se qualquer registro obrigatório do domínio falhar, abortar a transação daquele domínio e registrar falha fora dela, sem deixar vínculo parcial.
7. Não implementar dual-write, fila de sincronização contínua ou gatilho de escrita no legado.

### 12.5. Ordem de piloto para cadastros independentes

O primeiro piloto deve usar somente fixtures sintéticas, pequenas e autocontidas. A seleção de coleções deve ser explícita no envelope; não assumir que todas estão presentes.

Ordem sugerida para cadastros sem dependência referencial confirmada:
1. Categorias e Motivos de Acerto, mantendo os dois cadastros separados.
2. Fornecedores e Empregados, sem inferir relações entre eles.
3. Moradores, preservando bloco e apartamento como texto.
4. Condomínio e Conselho como estruturas separadas, sem FK inventada.
5. Plano de Contas.
6. Formas Monetárias e Contas Bancárias como cadastros independentes.

Essa ordem é uma sequência de ensaio, não uma afirmação de dependência funcional nem autorização de carga. Financeiro, Documentos e Acertos de Estoque ficam fora do primeiro piloto, pois exigem validação de referências ou arquivos. Dashboard/DRE não são importados.

### 12.6. Critérios de aceite específicos do controle

- [ ] Duas execuções concorrentes com a mesma identidade não criam duplicidade.
- [ ] Mesma identidade + mesmo hash resulta em `already_applied`.
- [ ] Mesma identidade + hash diferente resulta em conflito revisável, sem UPDATE.
- [ ] ID de destino ocupado sem vínculo de origem resulta em colisão.
- [ ] Uma identidade de origem não pode reivindicar destino já associado a outra origem.
- [ ] Lote não pode ser aplicado com hash diferente do aprovado.
- [ ] Falha transacional não deixa registro funcional sem proveniência nem proveniência sem registro funcional.
- [ ] Rollback não remove registros alterados ou referenciados após a criação.
- [ ] Ambiente de produção é recusado no nível da aplicação e da configuração de conexão.
- [ ] Relatórios não expõem conteúdo pessoal ou binário.



## 13. DDL de referência do controle

O desenho SQL inicial está em `sql-controle-lotes-importacao-rascunho.sql`. Ele descreve apenas:
- `migration_batches`: manifesto, snapshot, ambiente, modo, estado e aprovação vinculada ao hash;
- `migration_source_records`: identidade composta da origem, destino lógico, hash e lotes de criação/verificação.

O DDL é **rascunho não executável como migration**. Não foi aplicado, não cria tabelas funcionais, não concede permissões e não configura políticas RLS. A modelagem não substitui a validação do schema PostgreSQL local, das roles reais e das políticas necessárias.

Pontos que permanecem para a revisão técnica antes de gerar uma migration:
1. Conferir convenções e versão PostgreSQL efetivamente usadas pelo ambiente local descartável.
2. Definir a máquina de estados/transições protegida por lock, incluindo aprovação e falha.
3. Validar a estratégia de unicidade do destino para cada coleção e tipo de ID.
4. Definir retenção e auditoria append-only das decisões de conflito.
5. Criar testes concorrentes e transacionais contra PostgreSQL efêmero.
6. Revisar RLS/grants com roles dedicadas, sem habilitar runtime nem produção.

A coluna `approved_manifest_hash` deve ser igual a `manifest_hash`; qualquer alteração no manifesto exige nova revisão e nova aprovação. Nenhuma decisão humana pode autorizar atualização silenciosa de um vínculo de proveniência.
