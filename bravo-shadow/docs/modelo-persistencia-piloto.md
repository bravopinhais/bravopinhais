# Modelo de persistência — piloto Bravo Shadow

## Estado desta entrega

Projeto de banco documentado para revisão. **Nenhuma migration foi aplicada, nenhum projeto Supabase foi alterado e nenhum dado foi copiado.** Este documento não é um comando de execução.

A migration versionada ainda não foi criada. O rascunho SQL das tabelas do piloto está em [`sql-piloto-financeiro.sql`](./sql-piloto-financeiro.sql); ele não é um arquivo de migration e não deve ser aplicado diretamente. No ambiente local do projeto, primeiro verificar `supabase --version`, `supabase --help` e `supabase migration new --help`; em seguida gerar o arquivo com `supabase migration new bravo_pilot_financeiro` e copiar o SQL revisado para o arquivo timestampado criado pela CLI. A CLI v3 usa a stack local por padrão; operações hospedadas exigem `--remote` e confirmação. Não usar `--remote` nesta fase. A partir da CLI v3.4.0, `supabase init` cria `supabase/config.jsonc` por padrão; projetos existentes com `config.toml` continuam suportados.

## Decisões do piloto

- PostgreSQL em schema privado `bravo_shadow`, fora do schema exposto pela Data API.
- FastAPI é o único caminho de acesso da aplicação. O frontend não recebe chave privilegiada nem conecta diretamente ao banco.
- IDs permanecem `text` para preservar os identificadores prefixados já usados pela API sombra e permitir importação controlada futura.
- Valores monetários usam `Decimal` no contrato Python e `numeric(14,2)` no PostgreSQL; `float` não deve atravessar a camada de persistência. O schema HTTP de Financeiro já valida até 14 dígitos e 2 casas decimais.
- Datas operacionais usam `timestamptz`; datas de cadastro informadas pelo usuário permanecem separadas.
- Todas as tabelas terão `created_at`, `updated_at` e `version` para auditoria básica e concorrência otimista.
- Nenhuma regra nova de negócio será ativada sem comparar com o contrato original.

## Entidades do primeiro lote

### `bravo_shadow.plano_contas`

| Coluna | Tipo | Regra |
|---|---|---|
| id | text | PK; mantém prefixo pc_ |
| codigo | text | obrigatório |
| nome | text | obrigatório |
| tipo | text | somente Receita ou Despesa |
| created_at / updated_at | timestamptz | gerenciados pelo backend/banco |
| version | bigint | começa em 1; incrementa em atualização |

Índice único sugerido para `lower(codigo)`, sujeito à confirmação de paridade. Não aplicar até validar a regra de códigos duplicados.

### `bravo_shadow.financeiro`

| Coluna | Tipo | Regra |
|---|---|---|
| id | text | PK; mantém prefixo fin_shadow_ |
| tipo | text | Receber ou Pagar |
| plano_conta_id | text | FK opcional para plano_contas |
| historico | text | obrigatório |
| valor | numeric(14,2) | obrigatório; preservar sinal até confirmar regra |
| created_at / updated_at | timestamptz | auditoria |
| version | bigint | concorrência otimista |

A FK deve usar `ON DELETE RESTRICT`. O serviço deve converter string vazia em NULL no limite de persistência, mantendo o contrato HTTP atual se necessário. O bloqueio de exclusão passa a ser garantido no banco, não por callback em memória.

### `bravo_shadow.estoque`

| Coluna | Tipo | Regra |
|---|---|---|
| id | text | PK; mantém prefixo est_ |
| item | text | obrigatório |
| quantidade | integer | saldo atual |
| minimo / maximo | integer | limites |
| etiqueta | text | opcional; sem unicidade até validar |
| foto_nome | text | opcional |
| foto_compactada_gzip | text | legado compactado; armazenamento de arquivo será fase posterior |
| marca / linha / fabricante | text | extensão solicitada para rastreabilidade |
| data_cadastro | date | data de cadastro declarada; não inventar automaticamente |
| created_at / updated_at | timestamptz | auditoria |
| version | bigint | concorrência otimista |

### `bravo_shadow.acertos_estoque`

| Coluna | Tipo | Regra |
|---|---|---|
| id | text | PK |
| data | timestamptz | data/hora do movimento |
| tipo | text | Entrada ou Saída |
| produto_id | text | FK obrigatória para estoque |
| quantidade | integer | maior que zero |
| motivo | text | texto histórico preservado |
| created_at | timestamptz | auditoria |

A exclusão física de produto referenciado deve ser bloqueada por FK. O histórico de movimento não será apagado para simular estorno: correções futuras devem gerar movimento compensatório, após decisão explícita de negócio.

## Transações obrigatórias

1. **Criar acerto:** em uma única transação, bloquear a linha do produto (`SELECT ... FOR UPDATE`), validar o saldo conforme regra aprovada, atualizar quantidade e inserir histórico. Se qualquer etapa falhar, tudo sofre rollback.
2. **Editar/excluir acerto:** não permitir edição destrutiva de movimento que já alterou saldo sem recalcular saldo de forma transacional. No primeiro corte, manter somente exclusão bloqueada ou implementar estorno compensatório; não copiar a exclusão atual que apaga histórico sem reverter saldo.

**Política aplicada no adaptador persistente:** a API sombra retorna HTTP 409 ao tentar excluir um acerto existente. O histórico é preservado e o saldo não é alterado. O modo em memória mantém o comportamento legado apenas para testes; o usuário PostgreSQL dedicado também não deverá receber privilégio `DELETE` sobre `bravo_shadow.acertos_estoque`. O fluxo de estorno compensatório ainda não foi implementado.
3. **Excluir plano de contas:** a FK `ON DELETE RESTRICT` impede excluir conta usada por título financeiro, mesmo sob concorrência.
4. **Atualização concorrente:** UPDATE deve exigir a versão lida (`WHERE id = :id AND version = :expected_version`) e incrementar `version`; zero linhas atualizadas vira conflito HTTP 409.

## Contratos Python de transação

Foi criado `app/core/transactions.py` com o port `TransactionalInventoryRepository`: a implementação persistente deverá receber o movimento, o produto e a variação de saldo e executar tudo atomicamente. O protocolo `UnitOfWork` estabelece o limite transacional. São contratos arquiteturais, não um adaptador PostgreSQL pronto; nenhum driver ou conexão foi adicionado nesta etapa.

O schema HTTP de Financeiro passou a usar `Decimal` com limite de 14 dígitos e 2 casas decimais, alinhando a representação Python ao `numeric(14,2)`. Valores com mais de duas casas ou precisão acima do limite são rejeitados na validação da API.

## Segurança do banco

- Criar schema privado e não adicioná-lo à lista de schemas expostos da Data API.
- Revogar privilégios de `anon`, `authenticated` e `public` sobre schema e tabelas.
- Habilitar RLS em todas as tabelas do schema como defesa em profundidade, sem políticas permissivas nesta fase.
- O backend usará credencial server-side de privilégio mínimo armazenada em variável de ambiente/secret manager; nunca no HTML.
- Não definir política por `user_metadata`. A identidade Google/e-mail precisa ser validada no backend antes de estabelecer autorização.
- Antes de permitir acesso direto por cliente Supabase, desenhar políticas com `auth.uid()`, papéis e escopo real; não criar `USING (true)`.

## Contrato de repositórios Python

Criar interfaces independentes de FastAPI:
- `PlanoContasRepository`: listar, obter, inserir, atualizar com versão e excluir.
- `FinanceiroRepository`: listar, obter, inserir, atualizar com versão e excluir.
- `EstoqueRepository`: listar, obter, inserir, atualizar com versão e excluir.
- `AcertosEstoqueRepository`: listar e registrar movimento transacional.

Serviços recebem repositórios por injeção de dependência. Implementações `InMemory` continuam disponíveis apenas para testes unitários; implementação PostgreSQL será ativada somente com banco sombra isolado e configuração explícita. Não misturar fallback silencioso entre memória e banco.

## Sequência segura

1. Revisar este modelo e confirmar regras de exclusão/estoque.
2. Inicializar Supabase CLI localmente no diretório sombra; verificar `supabase --version` e `supabase --help`.
3. Gerar arquivo com `supabase migration new bravo_pilot_financeiro`.
4. Escrever SQL no arquivo gerado, revisar constraints, grants e RLS.
5. Subir somente stack local e testar migration do zero.
6. Criar testes de integração e concorrência; só depois considerar projeto Supabase de homologação dedicado.
7. Nunca apontar a sombra ao projeto de produção nem aplicar migration remota sem autorização específica.

## Pendências antes de codificar os repositórios

- Confirmar se códigos de Plano de Contas são realmente únicos no processo atual.
- Confirmar se o saldo negativo em saída de estoque continuará permitido ou será bloqueado como regra nova.
- Definir como tratar edição/exclusão de acertos antigos sem perder histórico nem distorcer saldo.
- Confirmar formato e fuso horário de data nos acertos legados.
- Definir política de retenção e migração de fotos compactadas.


## Adaptadores SQL Python — primeiro corte

Foi criado `app/core/postgres_repositories.py` com implementações DB-API de Plano de Contas e Financeiro. Cada operação abre uma unidade de trabalho própria; os parâmetros são enviados separadamente do SQL, o valor financeiro permanece `Decimal`, e a referência vazia de plano de contas é persistida como `NULL`. A FK do banco é a autoridade final para impedir exclusão de conta referenciada, com tradução de violação de integridade para HTTP 409.

**Limite importante:** estes adaptadores ainda não estão conectados aos serviços ou às rotas. A API ativa continua usando os repositórios em memória. Não foi instalado driver, configurada conexão, criada migration ou acessado qualquer projeto Supabase. Os testes usam cursor falso e precisam ser executados; não substituem teste de integração contra PostgreSQL local.

A coluna `version` é incrementada nas atualizações, mas os contratos atuais de serviço/HTTP ainda não transportam uma versão esperada. Portanto, não declarar controle otimista de concorrência concluído. Essa alteração requer evolução explícita do contrato e testes de conflito antes de ativar persistência.


## Falha durante o commit

A unidade de trabalho tenta executar `rollback` caso o próprio `commit` lance uma exceção, fecha a conexão em seguida e propaga a falha original. Há teste unitário com conexão falsa para esse cenário; a confirmação final depende de teste de integração em PostgreSQL local.


## Concorrência otimista — adaptadores SQL

Os adaptadores PostgreSQL agora têm `replace_if_version` para Plano de Contas e Financeiro. O UPDATE compara simultaneamente ID e versão esperada, incrementando `version` no sucesso. Se nenhuma linha for alterada, uma consulta dentro da mesma unidade de trabalho distingue ID inexistente (404) de versão obsoleta (409). Os métodos de leitura incluem a coluna `version`, e os schemas de resposta expõem esse valor.

**A proteção HTTP foi integrada para o adaptador em memória:** os PUTs exigem `If-Match` e os serviços fazem comparação e substituição atômicas. A injeção dos adaptadores PostgreSQL nas rotas continua pendente e só deve ocorrer após migration e teste local isolado.


## Precondição HTTP para concorrência otimista

Plano de Contas e Financeiro agora expõem `version` nos modelos de resposta. O POST também devolve um ETag forte (`"1"` na criação). O PUT exige `If-Match` com a versão que o cliente leu: cabeçalho ausente retorna 428, ETag inválida retorna 400 e conflito de versão retorna 409. O adaptador em memória implementa comparação e substituição atômicas com lock; os adaptadores PostgreSQL usam `UPDATE ... WHERE id = ... AND version = ...`. A API ainda opera em memória, então a ativação PostgreSQL permanece etapa separada e depende de migration/driver/ambiente local.


## Seleção de armazenamento na aplicação

Foi criado `app/core/storage.py` e a fábrica `create_app()` passou a aceitar seleção explícita do backend. O padrão é memória. O modo PostgreSQL exige uma `connection_factory` DB-API injetada pelo ambiente; ausência da fábrica gera erro de configuração, sem tentar conexão ou fallback. Nesta etapa, somente Plano de Contas e Financeiro são substituídos pelos adaptadores PostgreSQL; os demais módulos permanecem em memória.

A configuração não instala driver, não lê variáveis de credenciais, não cria schema e não abre conexão no startup. A ativação prática permanece bloqueada até migration local, driver escolhido e testes de integração em banco isolado. O endpoint de saúde informa apenas o backend configurado, não a disponibilidade do banco.


## Rascunho SQL do primeiro lote — revisão estática

O arquivo [`sql-piloto-financeiro.sql`](./sql-piloto-financeiro.sql) registra o DDL proposto para `bravo_shadow.plano_contas` e `bravo_shadow.financeiro`, alinhado aos nomes de colunas efetivamente usados por `postgres_repositories.py`. Inclui PKs textuais, checks de tipo, `numeric(14,2)`, versão, timestamps, FK com `ON DELETE RESTRICT`, índices e RLS habilitado sem policies ou grants para `anon`/`authenticated`.

**Não é migration e não foi executado.** A migration definitiva deve ser criada pela Supabase CLI no diretório `supabase/migrations/`, após conferir a versão e o help da CLI. A CLI v3.4.0 cria `config.jsonc` em projetos novos; não presumir que haverá `config.toml`. A stack local ainda não foi iniciada, e nenhuma conexão Supabase foi aberta.

### Revisões antes de aplicar localmente

- Confirmar que o usuário PostgreSQL usado pelo backend terá somente os privilégios necessários; o rascunho não concede acesso à Data API nem ao papel `service_role`.
- Manter o schema fora dos schemas expostos pela Data API.
- Não adicionar unicidade a `codigo` até a regra de duplicidade ser confirmada.
- Não aplicar esse DDL em qualquer projeto hospedado ou de produção.
- Depois de gerar a migration, revisar o SQL completo e validar com reset local desde banco vazio.


## Concorrência e unicidade do código

A edição de Plano de Contas e Financeiro usa compare-and-swap por `version`: o PostgreSQL atualiza somente quando o valor de `version` ainda corresponde ao `If-Match` recebido. O resultado da atualização já contém a nova versão, portanto a API devolve a entidade submetida com essa versão sem executar uma segunda leitura. Registro inexistente retorna 404; versão concorrente obsoleta retorna 409.

O código do Plano de Contas é comparado sem diferenciar maiúsculas/minúsculas na API. O rascunho SQL inclui índice único em `lower(codigo)` para garantir a mesma regra no banco e impedir duplicidade em requisições simultâneas. A validação prévia da API melhora a mensagem, mas a restrição do banco é a garantia final.

Essas alterações continuam sendo especificação/rascunho: o SQL não foi aplicado e os testes não foram executados.


## Piloto de Formas Monetárias — adaptador preparado

O serviço de Formas Monetárias foi desacoplado do dicionário em memória e passou a receber um repositório. O modo padrão continua em memória. Quando a aplicação recebe explicitamente o backend PostgreSQL e uma fábrica de conexão, o módulo usa `PostgresFormasMonetariasRepository`; não existe fallback silencioso.

O adaptador usa a tabela `bravo_shadow.formas_monetarias` e os campos `id`, `nome` e `multa_pct`. A multa é armazenada como `double precision`, com default 2.0, sem limites de faixa ou casas decimais que não existam no legado. Atualizações incrementam `version`; o contrato HTTP atual ainda não expõe controle otimista para este módulo.

O DDL da tabela foi acrescentado ao rascunho `sql-piloto-financeiro.sql`, com RLS habilitado e sem grants para clientes da Data API. **Continua sendo apenas rascunho**: não foi criada migration pela CLI, não houve conexão com PostgreSQL/Supabase e nenhuma tabela foi criada.

Foram acrescentados testes unitários com conexão/cursor falsos para mapear os campos, executar o CRUD e verificar 404 em atualização/exclusão de registros ausentes. Esses testes ainda precisam ser executados na CI; o fake não substitui teste real na stack PostgreSQL local.


## Extensão do rascunho SQL — Estoque e Acertos de Estoque

O rascunho SQL foi ampliado para incluir as tabelas `bravo_shadow.estoque` e `bravo_shadow.acertos_estoque`, com os campos correspondentes aos schemas atuais da API:

- Estoque mantém marca, linha, fabricante e data de cadastro, além dos campos legados de identificação e foto compactada.
- Acertos preserva data/hora, tipo, produto, quantidade, motivo textual e o identificador opcional do motivo.
- A FK de acerto para produto usa `ON DELETE RESTRICT`, preservando o histórico e impedindo apagar um produto que já possui movimentos.
- A tabela de acertos não cria ainda FK para `motivo_id`, pois o catálogo de motivos continua em memória e não existe tabela PostgreSQL correspondente neste corte.
- Ambas as tabelas habilitam RLS e revogam acesso da Data API, mantendo o acesso pretendido exclusivamente no backend.

### Regra transacional obrigatória para implementação

A criação de um acerto deve executar dentro de uma única transação PostgreSQL:

1. Selecionar o produto por ID com `FOR UPDATE`.
2. Retornar 404 se o produto não existir.
3. Calcular o novo saldo; em Saída, retornar 409 se a quantidade solicitada exceder o saldo disponível.
4. Atualizar o saldo e incrementar `version`.
5. Inserir o acerto com o mesmo ID/data gerados pela aplicação.
6. Confirmar a transação; qualquer falha antes do commit deve reverter saldo e histórico juntos.

O contrato de serviço atual ainda executa as duas operações separadamente em memória. O SQL ampliado é somente especificação: **não foi aplicado, não é migration e não habilita PostgreSQL para esses módulos**. Antes da ativação, será necessário implementar adaptadores DB-API, testes com PostgreSQL local isolado e migration criada pela Supabase CLI. A CLI/Docker não estão disponíveis no ambiente de trabalho atual, portanto essa validação local ainda não foi feita.


## Extensão do piloto — Categorias, Motivos e Documentos

O rascunho SQL foi ampliado com três tabelas e vínculos referenciais:

- `bravo_shadow.categorias`: catálogo de pastas/categorias usado por Documentos.
- `bravo_shadow.motivos_acerto`: catálogo de motivos referenciado por Acertos de Estoque.
- `bravo_shadow.documentos`: mantém pasta textual, título, nome do arquivo e o conteúdo legado `arquivoCompactadoGzip` em texto; `categoria_id` é opcional.

As FKs usam `ON DELETE RESTRICT`. Assim, categorias com documentos e motivos utilizados em movimentações não podem ser removidos, inclusive em operações concorrentes. IDs nulos continuam permitidos para documentos e acertos antigos sem vínculo. O texto `pasta` e o texto `motivo` permanecem armazenados como snapshot histórico, além dos IDs referenciais.

### Adaptadores Python

Foi criado `app/core/postgres_catalogs.py` com repositórios DB-API para Categorias, Motivos de Acerto e Documentos. O modo PostgreSQL agora injeta esses adaptadores nos serviços correspondentes; o modo memória continua como padrão e usa repositórios isolados por aplicação. Erros de FK ao excluir categorias/motivos são traduzidos para HTTP 409. Documentos preservam o conteúdo compactado legado sem conversão nem migração de arquivos para Supabase Storage.

O SQL continua sendo apenas rascunho. Não foi criada migration pela CLI, não houve conexão a PostgreSQL real e nenhuma tabela foi aplicada. Os testes adicionados usam conexões/cursors falsos; a validação em banco local isolado continua pendente.

### Limites preservados

- O armazenamento de arquivos permanece no campo legado compactado em texto; política de tamanho, recuperação, preview e migração para object storage seguem para uma etapa própria.
- A autenticação Google/e-mail e autorização server-side ainda não foram concluídas; não expor o schema privado à Data API.
- O backend ainda não tem pool de conexões.
- Nenhum dado de produção foi copiado ou utilizado.


## Extensão — Moradores, Fornecedores, Empregados e Contas Bancárias

Foram adicionados adaptadores DB-API em `app/core/postgres_cadastros.py` para os quatro cadastros, mantendo os campos e nomes do contrato atual:

- **Moradores:** bloco, apartamento, nome, e-mail, telefone, CPF, nome do pet e vaga de garagem.
- **Fornecedores:** CNPJ e razão social.
- **Empregados:** nome, cargo, empresa, endereço, telefone e contato de emergência.
- **Contas Bancárias:** banco e saldo informado.

O rascunho SQL cria tabelas privadas para os quatro cadastros, com IDs textuais, timestamps e versão. Os campos pessoais são mantidos apenas no schema privado, com RLS habilitado, sem policies e com revogação de grants de `public`, `anon`, `authenticated` e `service_role`. Não foram adicionadas restrições de unicidade para CPF/CNPJ nem vínculos entre contas bancárias e lançamentos financeiros, pois essas regras não foram confirmadas no contrato legado. O saldo bancário continua sendo saldo informado, não conciliação bancária.

O modo PostgreSQL injeta os novos repositórios nos serviços. O modo memória continua padrão. Testes DB-API simulados cobrem mapeamento de campos e injeção dos quatro repositórios.

**Limites:** não houve importação de cadastros existentes, conexão a PostgreSQL real, criação/aplicação de migration ou revisão jurídica/operacional de retenção de dados pessoais. Antes de dados reais, ainda são necessários banco local isolado, política de acesso por identidade Google validada no backend, regras de unicidade aprovadas e avaliação de privacidade.


## Proteção do saldo após histórico de estoque

No modo PostgreSQL, a edição cadastral de um produto bloqueia a linha com `FOR UPDATE` e verifica se já existem acertos vinculados. Se houver histórico, a quantidade não pode ser alterada pela edição geral: mudanças de saldo devem passar pelo fluxo transacional de Entrada/Saída, preservando a trilha de movimentos. A edição de outros campos cadastrais continua permitida. A regra é serializada com a criação de movimentos pelo mesmo bloqueio de linha.


## Revisão de integridade — Contas Bancárias

- O campo `banco` agora remove espaços externos e rejeita valores compostos apenas por espaços, tanto na criação quanto na atualização, por meio do schema compartilhado.
- O saldo continua como `Decimal` com até 14 dígitos e duas casas decimais; não foi criada regra para impedir saldo negativo, pois isso depende de confirmação operacional.
- O CRUD atual permite atualizar banco e saldo diretamente. Esse saldo permanece um valor informado/manual, não um saldo calculado por extrato ou conciliação.
- Não existe coluna de conta bancária em `financeiro`, nem FK ou regra de associação entre títulos e contas bancárias. Portanto, não se presume que um lançamento pertença a determinada conta, e nenhuma conciliação automática é possível nesta versão.
- A exclusão de conta bancária não possui bloqueio por lançamentos financeiros, pois não há vínculo referencial no modelo atual. Antes de introduzir esse vínculo, é necessário definir se títulos podem ser associados a uma conta, em qual etapa, e como tratar transferências, pagamentos parciais e conciliação.
- Foram acrescentados testes de normalização no POST e PUT e rejeição de nome em branco. Os testes ainda não foram executados; o adaptador PostgreSQL ainda depende de validação em banco local isolado.


## Revisão de integridade — Moradores e Unidades

- Os campos textuais do cadastro agora removem espaços externos na entrada, tanto em criação/edição quanto no schema de importação que herda o modelo-base.
- Campos obrigatórios `bloco`, `apartamento` e `nome` continuam obrigatórios; valores compostos apenas por espaços são rejeitados após a normalização.
- Campos opcionais de contato e identificação continuam aceitando vazio. A normalização não remove pontuação nem altera o formato legado de CPF e telefone.
- Não foi ativada validação de dígitos de CPF, unicidade de CPF, unicidade de unidade ou validação estrita de formato de e-mail. O teste legado já utiliza CPF abreviado, e essas regras exigem saneamento/decisão de negócio antes de bloquear cadastros existentes ou importações.
- A busca por nome/apartamento e o filtro por bloco continuam sem alteração funcional.
- Foram acrescentados testes de normalização, rejeição de campo obrigatório só com espaços e compatibilidade com campos opcionais vazios. Os testes ainda não foram executados.
- O cadastro contém dados pessoais (inclusive CPF e contato). Antes de qualquer dado real, continuam obrigatórios autenticação Google validada no backend, matriz de autorização aprovada, banco privado com grants mínimos e definição de retenção/acesso. Nenhuma dessas proteções foi presumida como concluída nesta revisão.


## Revisão de integridade — Fornecedores

- Os campos obrigatórios `cnpj` e `razaoSocial` removem espaços externos na criação e atualização. Valores vazios ou compostos apenas por espaços são rejeitados pelo limite mínimo após a normalização.
- A pontuação e a representação informada do CNPJ são preservadas; não há conversão automática para somente dígitos nem validação dos dígitos verificadores nesta etapa. Isso evita alterar identificadores legados e não impede cadastro histórico atualmente aceito pela API.
- Não foi criada unicidade de CNPJ nem bloqueio de duplicidade. Antes disso, será necessário identificar registros duplicados existentes e confirmar a regra operacional para matriz/filial, fornecedores repetidos ou cadastros históricos.
- Razão social não é convertida para maiúsculas/minúsculas; apenas espaços externos são removidos.
- Foram acrescentados testes para normalização no POST/PUT, rejeição de CNPJ em branco e preservação do formato pontuado. Os testes ainda não foram executados.
- A tabela de fornecedores contém identificador empresarial. Antes de importar dados reais, manter as proteções de banco privado, autenticação e autorização server-side pendentes já documentadas.


## Revisão de integridade — Empregados

- Todos os campos textuais do cadastro removem espaços externos na criação e atualização: nome, cargo, empresa, endereço, telefone e contatos de emergência.
- Nome e cargo continuam obrigatórios; valores compostos apenas por espaços são rejeitados depois da normalização. Empresa, endereço e contatos permanecem opcionais e aceitam vazio.
- Telefones preservam pontuação, espaços internos e demais caracteres informados; não foi imposta validação de DDD, quantidade de dígitos ou máscara, para não bloquear registros legados.
- Não foram criadas regras de unicidade para nome, telefone ou contato de emergência. Nome não é identificador único de empregado.
- Foram acrescentados testes para normalização dos campos, rejeição de cargo em branco e compatibilidade com campos opcionais vazios. Os testes ainda não foram executados.
- O cadastro pode conter endereço e dados de contato pessoal. Antes de importar dados reais, permanecem necessários controles de acesso server-side, autenticação validada, matriz de permissões aprovada e política de retenção.


## Revisão de integridade — Condomínio e Conselho

- **Condomínio:** os campos textuais do perfil são normalizados removendo espaços externos. O endpoint continua sendo um PATCH semântico via PUT: campos omitidos permanecem intactos e valores `null` não apagam dados existentes; string vazia continua sendo aceita para permitir limpar campos opcionais.
- **Conselheiros:** nome, cargo, bloco/apartamento e telefone removem espaços externos na criação e atualização. Nome e cargo seguem obrigatórios; valores somente com espaços são rejeitados após normalização. Bloco/apartamento e telefone continuam opcionais.
- A pontuação e o formato de telefones são preservados; não foram adicionadas máscaras, validação de DDD ou normalização de números.
- Não foi criado vínculo por FK entre conselheiros e moradores/unidades: o campo `BlocoAp` é texto livre no contrato atual. Converter para relacionamento exigiria identificar unidades de referência e definir comportamento para mudanças de bloco/apartamento.
- Não foram adicionadas regras de unicidade para nome, cargo, e-mail, telefone ou unidade. O cadastro pode conter conselheiros com nomes iguais e o sistema não tem identificador de unidade estruturado neste módulo.
- Foram adicionados testes para normalização, preservação de campos omitidos, limpeza por string vazia e rejeição de campos obrigatórios em branco. Os testes ainda não foram executados.
- Os dados de condomínio e conselho não devem ser tratados como protegidos por autorização funcional: as rotas de negócio continuam sem dependências de autorização enquanto a matriz de permissões não for aprovada e a validação do token Google não for confirmada.


## Revisão de integridade — Categorias e Motivos de Acerto

- Os nomes de Categorias e Motivos de Acerto agora removem espaços externos na entrada. Valores vazios ou compostos apenas por espaços são rejeitados pela validação de tamanho mínimo após a normalização.
- Não foi criada unicidade de nome nem comparação sem diferenciar maiúsculas/minúsculas. O contrato atual não confirma se nomes iguais podem representar categorias/motivos distintos, inclusive em pastas ou fluxos diferentes; impor unicidade poderia bloquear cadastros existentes.
- Categorias são referenciadas por Documentos por meio de `categoria_id`; a exclusão de categoria em uso é bloqueada pelo serviço em memória e pela FK `ON DELETE RESTRICT` no rascunho PostgreSQL.
- Motivos são referenciados por Acertos de Estoque por meio de `motivo_id`; a exclusão de motivo utilizado é bloqueada pelo serviço em memória e pela FK `ON DELETE RESTRICT` no rascunho PostgreSQL. O texto do motivo permanece como snapshot no movimento para preservar o histórico.
- Os campos de nome não são convertidos para maiúsculas/minúsculas, e nenhum texto de histórico é reescrito. As regras de vínculo existentes foram preservadas.
- Foram adicionados testes para normalização e rejeição de nomes somente com espaços. Os testes ainda não foram executados; a integridade referencial PostgreSQL segue dependente de migration e validação em banco local isolado.


## Revisão de integridade — Gestão de Documentos

- Os metadados textuais `pasta`, `titulo` e `nomeArquivo` removem espaços externos. Título e nome do arquivo permanecem obrigatórios; valores compostos apenas por espaços são rejeitados após normalização.
- `categoriaId` remove espaços externos e converte string vazia em `null`, mantendo o documento sem categoria. Quando há ID, o serviço confirma a existência da categoria e usa o nome dela como pasta; no PostgreSQL, a FK também protege contra referências inválidas e exclusão concorrente.
- **O conteúdo compactado `arquivoCompactadoGzip` não é normalizado nem reescrito.** O valor recebido é preservado exatamente, inclusive espaços externos, para não alterar conteúdo legado. O campo continua obrigatório.
- O contrato e o schema SQL armazenam o conteúdo compactado como texto. Não foi introduzido limite de tamanho, decodificação Base64, validação do cabeçalho GZIP, antivírus ou armazenamento externo; essas decisões exigem conhecer o formato real dos arquivos legados e o volume esperado.
- A atualização continua substituindo o registro completo via PUT; não foi alterada para PATCH. O nome original do arquivo é preservado como metadado e não é usado como caminho de armazenamento.
- Foram adicionados testes para normalização de metadados, categoria opcional, rejeição de título/nome de arquivo em branco e preservação byte a byte do valor textual compactado. Os testes ainda não foram executados.
- Documentos podem conter informações pessoais ou administrativas. As rotas de negócio seguem sem autorização funcional; não disponibilizar documentos reais externamente até autenticação Google validada, matriz de permissões aprovada e controles de acesso implementados.


## Revisão de integridade — Estoque e Inventário

- Os metadados textuais do produto (item, etiqueta, fotoNome, marca, linha e fabricante) removem espaços externos na entrada. O nome do item continua obrigatório e valores compostos apenas por espaços são rejeitados.
- dataCadastro permanece uma string ISO AAAA-MM-DD no contrato HTTP para preservar compatibilidade com o frontend. O backend remove espaços externos, valida a data real do calendário e normaliza o valor; campo vazio permanece como não informado. O adaptador PostgreSQL converte vazio para NULL na coluna date.
- fotoCompactadaGzip não é normalizado nem reescrito, preservando exatamente o conteúdo legado recebido. Não foram adicionados limites de tamanho, validação Base64/GZIP, antivírus ou migração para armazenamento externo.
- Os campos marca, linha, fabricante e dataCadastro já percorrem schema, serviço e adaptador PostgreSQL, além das colunas correspondentes no rascunho SQL. A interface HTML da sombra ainda não contém um formulário de cadastro de estoque conectado a essa API; portanto, a integração visual permanece pendente.
- Quantidade, mínimo e máximo continuam inteiros com os valores padrão atuais. Não foi imposta regra para saldo negativo, mínimo maior que máximo, máximo igual a zero ou limites de reposição, pois o significado operacional desses campos precisa ser confirmado. Movimentos registrados continuam sendo o caminho protegido para alterar saldo no modo PostgreSQL.
- Foram acrescentados testes de normalização dos metadados, preservação do conteúdo compactado, validação de data e rejeição de nome em branco. Os testes foram escritos, mas ainda não executados; a persistência PostgreSQL também depende de teste de integração em banco local isolado.
- A exclusão de produto com movimentos segue protegida pela FK no rascunho SQL. As rotas de negócio continuam sem autorização funcional; não inserir dados reais nem expor o módulo até concluir autenticação, matriz de permissões e controles de acesso.


## Revisão de integridade — Acerto de Estoque

- O acerto aceita somente os tipos Entrada e Saída, exige quantidade inteira maior que zero e exige produto e motivo textual não vazios. Produto e motivo removem espaços externos; motivoId opcional também é normalizado, e string vazia equivale a ausência de vínculo.
- A criação verifica a existência do produto e, quando informado, a existência do motivo cadastrado. Se o motivoId for válido, o nome atual do catálogo é gravado como snapshot no campo motivo do movimento.
- A saída não pode exceder o saldo disponível. No PostgreSQL, o produto é bloqueado com SELECT FOR UPDATE e a atualização do saldo e a inserção do movimento ocorrem na mesma transação, evitando saldo negativo e perda de atualização concorrente.
- Movimentos são imutáveis em ambos os modos de armazenamento: a rota DELETE retorna 409 para um movimento existente e 404 para um ID inexistente. Correções deverão ser feitas por lançamento compensatório; esse fluxo ainda não foi implementado.
- Produtos com movimentações não podem ser excluídos. Também não podem ter o saldo alterado diretamente pelo PUT; a alteração cadastral permanece permitida quando mantém o saldo atual. O saldo deve ser modificado por Entrada/Saída.
- O verificador de referência usa busca protegida pelo lock do repositório em memória e a FK ON DELETE RESTRICT no PostgreSQL. O adaptador PostgreSQL mantém também bloqueio transacional do produto durante o registro.
- Foram adicionados testes para normalização de campos, quantidade positiva, rejeição de textos em branco, imutabilidade do movimento, bloqueio de exclusão/alteração direta do saldo do produto e manutenção de alterações cadastrais sem mudar saldo. Os testes foram escritos, mas ainda não executados.
- O repositório em memória é destinado a testes e desenvolvimento local, não oferece garantia de transação concorrente equivalente ao PostgreSQL e não deve ser usado em produção. A validação definitiva do fluxo persistente depende de teste em banco PostgreSQL local isolado.
- A rota DELETE legada permanece no contrato por compatibilidade, mas responde conflito; não existe capacidade de autorização para excluir movimentos. As rotas de negócio continuam sem autorização funcional até aprovação da matriz e validação completa da autenticação.
