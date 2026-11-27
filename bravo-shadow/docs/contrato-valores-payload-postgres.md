# Contrato estrito de valores no limite PostgreSQL

## Objetivo

O adaptador agora valida os valores do payload antes de abrir cursor ou executar INSERT. O contrato é derivado dos tipos e restrições presentes nos rascunhos SQL atuais; não substitui a futura comparação com migrations versionadas e catálogo PostgreSQL.

## Regras

- Texto: recebe somente `str`; não converte números, objetos ou booleanos em texto.
- Decimais `numeric(14,2)` e `numeric(14,3)`: aceita texto decimal canônico, inteiro ou `Decimal`; rejeita float, booleano, vírgula decimal, NaN, infinito, excesso de escala e overflow. A contagem de dígitos considera também expoentes positivos de `Decimal` e trata zero sem consumir precisão. Não arredonda.
- Estoque: quantidades, mínimo, máximo e valor unitário não podem ser negativos; movimento exige quantidade estritamente positiva.
- Datas: `estoque.data_cadastro` aceita data ISO real ou objeto `date`; não aceita formato local nem datetime.
- Instantes: `acertos_estoque.data` exige datetime com timezone ou ISO-8601 com offset explícito.
- Enumerações: exige literal exato conforme CHECK do DDL.
- `formas_monetarias.multa_pct`: aceita número finito, sem booleano; inteiros fora da faixa representável como float finito são rejeitados.

Campos explicitamente nulos permanecem nulos para que a constraint SQL de nulabilidade seja a autoridade final. Nenhuma coerção ou mutação é aplicada ao payload.

## Limitações conscientes

O validador cobre tipos e regras numéricas conhecidas do DDL funcional. Não substitui validação de NOT NULL, FKs, unicidade, permissões, CHECKs ainda não modelados nem inspeção de catálogo. Os rascunhos SQL não foram executados. Nenhum banco foi conectado.

Casos sintéticos adicionais cobrem expoentes positivos, limite de dígitos inteiros de `numeric(14,2)`, zero com expoente e inteiro fora da faixa de float. Os testes foram adicionados e não executados.
