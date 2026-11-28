# Contrato do pacote versionado de evidências de preparação

**Status:** especificação técnica; ainda não é um formato operacional nem autoriza importação.  
**Escopo:** Shadow, dados sintéticos/anônimos, validação local e sem conexão com banco.

## 1. Objetivo e regra de confiança

O pacote deve permitir reconstruir, de forma determinística, a cadeia de evidências usada pelo pré-flight. Nenhum resultado derivado enviado pelo pacote será considerado confiável apenas por estar serializado.

A validação deve reconstruir os objetos tipados e recalcular:
1. validação estrutural do envelope;
2. inventário de identidades e correspondência exata dos candidatos;
3. plano de dry-run;
4. relatório agregado;
5. manifesto e seu hash;
6. registro de decisões e sua integridade.

A cadeia termina em evidência para revisão humana. Não aprova, não executa e não autoriza escrita.

## 2. Envelope externo proposto — versão 1

Objeto JSON UTF-8 com exatamente estas chaves:

- `packageFormatVersion`: inteiro JSON igual a `1` (booleano não é inteiro válido);
- `packageType`: texto literal `bravo-migration-evidence`;
- `sourceEnvelope`: objeto original do envelope, preservado sem coerção;
- `sourceEnvelopeRawSha256`: SHA-256 hexadecimal minúsculo declarado dos bytes originais do envelope, quando o pacote for produzido a partir de arquivo. É metadado de proveniência, não verificável contra o objeto `sourceEnvelope` sem os bytes originais;
- `candidates`: lista ordenada de candidatos tipados;
- `alreadyKnownSources`: lista ordenada de identidades previamente conhecidas, explicitamente fornecidas como evidência;
- `manifestContext`: exatamente `environment`, `importerVersion`, `mappingVersion` e `createdAt`;
- `packageSha256`: SHA-256 do JSON canônico de todos os campos anteriores, excluindo este próprio campo.

O pacote não inclui `PreflightResult`, `PreflightReport` ou `DecisionRegister` como autoridade. Esses objetos serão sempre reconstruídos. Se uma versão futura incluir cópias informativas desses resultados, elas serão apenas comparadas com os resultados reconstruídos, nunca aceitas como fonte.

## 3. Forma dos candidatos e identidades

Cada candidato contém exatamente:

- `identity`: objeto com `sourceSystem`, `sourceCollection`, `legacyId`;
- `sourceRecordHash`: SHA-256 hexadecimal minúsculo;
- `destinationIdExists`: booleano estrito;
- `existingMapping`: `null` ou objeto com `sourceRecordHash` e `destinationId`;
- `references`: lista de identidades no mesmo formato.

Cada identidade contém exatamente os três campos definidos acima, todos textos não vazios. Não normalizar, aparar ou converter IDs durante a leitura: a reconstrução deve preservar os valores e deixar os validadores de domínio rejeitarem os inválidos.

As listas de candidatos e identidades conhecidas preservam a ordem recebida. Duplicidades não devem ser silenciosamente removidas: duplicidade de candidato é erro de pré-flight; identidades conhecidas duplicadas devem ser rejeitadas pelo leitor do pacote.

## 4. Canonicalização e integridade

- UTF-8 estrito; JSON sem chaves duplicadas e sem NaN/Infinity.
- Canonicalização do pacote: UTF-8, chaves de objeto ordenadas, separadores compactos, `ensure_ascii=false` e `allow_nan=false`.
- Hashes em hexadecimal minúsculo com exatamente 64 caracteres.
- Rejeitar hash ausente, inválido ou divergente; nunca recalcular e substituir silenciosamente o valor apresentado.
- Limite inicial de leitura: 10 MiB, alinhado ao leitor de envelope existente; o pacote deve ter seu próprio limite explícito antes de ser aceito.
- Rejeitar campos desconhecidos e obrigatórios ausentes em todos os níveis.
- Rejeitar versão ou `packageType` desconhecidos. Não tentar migração automática entre versões.
- O leitor atual valida estrutura, tipos e hashes, mas **ainda não faz uma inspeção semântica completa dos valores arbitrários dentro de cada registro de origem**. Portanto, não se deve afirmar que ele detecta ou bloqueia, de forma geral, caminhos, URLs, nomes de módulos/funções, callbacks, credenciais, tokens, cookies, strings de conexão ou dados pessoais reais. Esses conteúdos não são necessários para a validação e devem ser excluídos na preparação do pacote; nesta etapa, só podem ser usados dados sintéticos ou devidamente anonimizados.
- Antes de qualquer CLI ou ingestão, será obrigatório definir um esquema permitido por coleção e uma validação explícita dos campos, com testes para caminhos, URLs, referências executáveis e padrões de segredo. Uma varredura genérica por palavras ou expressões regulares, isoladamente, não será considerada prova suficiente de sanitização.

O hash do arquivo bruto do envelope, o `snapshotHash` interno e o hash do pacote são evidências distintas. O hash do pacote protege a integridade do campo `sourceEnvelopeRawSha256`, mas não prova que esse digest corresponde ao objeto `sourceEnvelope` embutido: para essa comprovação seria necessário incluir e conferir os bytes originais do envelope. O leitor valida o formato do digest declarado, sem afirmar que o verificou. O leitor existente deliberadamente não presume que o hash bruto e `snapshotHash` sejam equivalentes. Também não se deve recalcular o `snapshotHash` a partir dos candidatos até que o contrato oficial do exportador defina formalmente o mesmo algoritmo e escopo.

## 5. Reconstrução e verificações obrigatórias

A rotina de leitura deve:

1. decodificar o pacote com UTF-8 estrito, rejeitar chaves JSON duplicadas, números não finitos e excesso de tamanho;
2. validar o esquema externo e todos os subobjetos com igualdade exata de chaves;
3. validar o hash do pacote antes de construir objetos de domínio;
4. validar o envelope com `validate_batch_envelope`;
5. reconstruir `SourceIdentity`, `ExistingSourceMapping` e `DryRunCandidate` sem coerção;
6. executar `run_migration_preflight` usando somente as identidades conhecidas incluídas no pacote;
7. reconstruir `PreflightReport` com `build_preflight_report`;
8. reconstruir `MigrationManifest` com o contexto versionado e conferir a cadeia com `verify_manifest_against_batch`;
9. reconstruir `DecisionRegister` com `build_decision_register` e conferir com `verify_decision_register_against_batch`;
10. retornar um resultado de validação imutável, contendo hashes, contagens e códigos de erro — sem expor payloads de origem desnecessariamente.

Qualquer falha encerra a validação em estado inválido. Não corrigir automaticamente dados, não descartar candidatos e não produzir um pacote “reparado”.

## 6. Isolamento e segurança

O leitor e o validador do pacote devem ser funções puras ou operar somente sobre bytes fornecidos pelo chamador. Não podem abrir caminhos recebidos no JSON, acessar rede, consultar variáveis de ambiente, abrir conexão PostgreSQL ou importar código indicado pelo pacote.

A validação do pacote não importa nem instancia a fábrica de conexão de migração. A credencial `BRAVO_MIGRATION_DATABASE_URL` permanece fora do pacote e fora dos argumentos de linha de comando.

## 7. Testes negativos mínimos antes de qualquer CLI

- versão externa desconhecida, campo ausente e campo extra;
- chave JSON duplicada, UTF-8 inválido, JSON truncado, NaN/Infinity e arquivo acima do limite;
- hash do pacote divergente; digest bruto declarado malformado; se os bytes originais forem incluídos numa revisão futura, digest bruto divergente;
- identidade/candidato com tipo incorreto, hash malformado ou booleano no lugar de inteiro;
- referência e mapeamento malformados;
- candidato duplicado, faltante, inesperado ou de outro sistema de origem;
- identidade conhecida duplicada;
- manifesto adulterado, relatório divergente e registro de decisões adulterado;
- strings que pareçam caminhos, URLs, módulos, callbacks ou credenciais;
- comprovação de que validação inválida não tenta abrir conexão nem acessa rede/arquivos.

## 8. Gate para evolução

O leitor inicial já foi implementado em `backend/app/core/migration_evidence_package.py`; sua cobertura de testes ainda precisa ser ampliada para todos os casos desta especificação. A CLI manual continua bloqueada até existir pacote validado e um fluxo separado que exija ambiente Shadow descartável, apresente lote/hash/contagens para revisão e solicite confirmação explícita antes de qualquer conexão. Este contrato, isoladamente, não libera importação, não declara o banco pronto e não altera a versão principal.
