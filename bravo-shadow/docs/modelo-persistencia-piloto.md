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
