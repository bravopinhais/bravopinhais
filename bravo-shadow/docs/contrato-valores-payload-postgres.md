# Contrato estrito de valores no limite PostgreSQL

## Objetivo

O adaptador agora valida os valores do payload antes de abrir cursor ou executar INSERT. O contrato é derivado dos tipos e restrições presentes nos rascunhos SQL atuais; não substitui a futura comparação com migrations versionadas e catálogo PostgreSQL.

## Regras

- Texto: recebe somente `str`; não converte números, objetos ou booleanos em texto. Campos textuais obrigatórios também rejeitam string vazia ou composta apenas por espaços.
- Decimais `numeric(14,2)` e `numeric(14,3)`: aceita texto decimal canônico, inteiro ou `Decimal`; rejeita float, booleano, vírgula decimal, NaN, infinito, excesso de escala e overflow. A contagem de dígitos considera também expoentes positivos de `Decimal` e trata zero sem consumir precisão. Não arredonda.
- Estoque: quantidades, mínimo, máximo e valor unitário não podem ser negativos; movimento exige quantidade estritamente positiva.
- Datas: `estoque.data_cadastro` aceita data ISO real ou objeto `date`; não aceita formato local nem datetime.
- Instantes: `acertos_estoque.data` exige datetime com timezone ou ISO-8601 com offset explícito.
- Enumerações: exige literal exato conforme CHECK do DDL, incluindo `plano_contas.tipo`, `financeiro.tipo`, `estoque.status`, `usuarios.perfil`, `usuarios.status` e `acertos_estoque.tipo`.
- `formas_monetarias.multa_pct`: aceita número finito, sem booleano; inteiros fora da faixa representável como float finito são rejeitados.

Valores `null` só são aceitos nas quatro colunas explicitamente nullable do contrato (`financeiro.plano_conta_id`, `estoque.data_cadastro`, `documentos.categoria_id`, `acertos_estoque.motivo_id`); nos demais campos são rejeitados antes do INSERT. Campos opcionais com DEFAULT devem ser omitidos para que o PostgreSQL aplique o padrão; o adaptador não injeta defaults. Nenhuma coerção ou mutação é aplicada ao payload.

## Limitações conscientes

O adaptador compara a presença dos campos obrigatórios com a lista derivada de NOT NULL sem DEFAULT, rejeita campos textuais obrigatórios vazios e deixa defaults SQL para colunas omitidas. Isso não substitui validação de FKs, unicidade, permissões, CHECKs ainda não modelados nem inspeção de catálogo. Os rascunhos SQL não foram executados. Nenhum banco foi conectado.

Casos sintéticos adicionais cobrem expoentes positivos, limite de dígitos inteiros de `numeric(14,2)`, zero com expoente, inteiro fora da faixa de float, literais válidos/inválidos de perfil e status e campos textuais obrigatórios vazios. Os testes foram adicionados e não executados.


## Integridade referencial e vínculos legados

A reconciliação de referências legadas é somente leitura e produz contagens agregadas, sem expor IDs ou valores dos registros. Até aqui, somente dois vínculos de origem foram confirmados: `financeiro.planoContaId` para `plano_contas.id` (opcional) e `acertos_estoque.produtoId` para `estoque.id` (obrigatório). Referências ausentes, inválidas, órfãs ou com destino duplicado/malformado bloqueiam a classificação como resolvida.

O DDL também contém FKs para `documentos.categoria_id` e `acertos_estoque.motivo_id`, ambas opcionais, mas esses campos ainda são vínculos exclusivos do modelo de destino: não foram presumidos como campos equivalentes da origem. Todas as FKs usam `ON DELETE RESTRICT`, evitando apagar silenciosamente registros referenciados.

A reconciliação prévia não substitui as FKs no PostgreSQL. O fechamento estático agora confere nome da constraint, coluna de origem, tabela/coluna de destino, nulabilidade e política de exclusão. Não houve importação nem conexão com banco; os testes foram adicionados e não executados.


## Identidade, duplicidade e reexecução segura

O inventário de origem contabiliza IDs ausentes e duplicados por coleção, sem expor os valores. A identidade legada é composta por sistema, coleção e ID opaco; espaços em branco não são identidade válida e zeros à esquerda permanecem significativos. IDs duplicados, ausentes ou registros que não sejam objetos mantêm a origem em revisão.

A tabela de proveniência fecha a idempotência no banco com chave primária composta por `source_system`, `source_collection` e `legacy_id`, além de unicidade global do par `destination_collection`/`destination_id`. O hash do registro exige 64 caracteres hexadecimais minúsculos. As referências aos lotes inicial e último verificado também são protegidas por FKs compostas que incluem o sistema de origem.

Uma repetição só é considerada já aplicada quando o hash e o destino permanecem iguais. Mudança no conteúdo, destino divergente, mapeamento malformado ou colisão de ID no destino bloqueiam nova gravação e exigem revisão. O adaptador usa bloqueio transacional por identidade e a persistência de proveniência não retargeta silenciosamente um registro.

Essas proteções foram conferidas por revisão estática e casos sintéticos adicionados. Não houve execução dos testes, conexão PostgreSQL ou importação de dados.
