# Modelo de persistência — piloto Bravo Shadow

## Estado desta entrega

Projeto de banco documentado para revisão. **Nenhuma migration foi aplicada, nenhum projeto Supabase foi alterado e nenhum dado foi copiado.** Este documento não é um comando de execução.

A migration versionada deverá ser gerada no ambiente local com a versão de Supabase CLI efetivamente instalada usando o comando documentado `supabase migration new bravo_pilot_financeiro_estoque`, e revisada antes de qualquer aplicação. A CLI v3 mudou o padrão para local e exige `--remote` para operações hospedadas; não usar comandos remotos nesta etapa.

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
- Habilitar RLS nas quatro tabelas como defesa em profundidade, sem políticas permissivas nesta fase.
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
3. Gerar arquivo com `supabase migration new bravo_pilot_financeiro_estoque`.
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
