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
