# Auditoria de compatibilidade — controle de migração x schemas Shadow

**Status:** revisão estática de código e SQL; documentação somente.  
**Branch:** `bravo-shadow`.  
**Não realizado:** execução de testes, conexão PostgreSQL, aplicação de migration ou importação de dados.

## 1. Escopo revisado

Arquivos consultados:
- `docs/desenho-controle-lotes-migracao.md`
- `docs/especificacao-importador-migracao-v1.md`
- `docs/sql-piloto-financeiro.sql`
- `backend/app/core/postgres.py`
- `backend/app/core/transactions.py`
- `backend/app/core/repositories.py`
- `backend/app/core/postgres_repositories.py`
- `backend/app/core/postgres_inventory.py`
- `backend/app/core/postgres_catalogs.py`
- `backend/app/core/postgres_cadastros.py`
- schemas Pydantic de Financeiro, Estoque, Acertos de Estoque e Documentos.

A revisão é amostral, focada nos contratos e nos fluxos que afetam identidade, idempotência e integridade da importação. Não equivale a uma revisão integral de todos os módulos.

## 2. Incompatibilidades e decisões necessárias

### 2.1 Data de acerto: texto na API, timestamp no SQL

**Evidência no código:**
- `Acerto.data` é declarado como `str` em `modules/acertos_estoque/schemas.py`.
- A ficha do legado documenta data como texto no formato pt-BR.
- O DDL declara `acertos_estoque.data timestamptz`.
- O repositório PostgreSQL envia `item.data` diretamente como parâmetro e, na leitura, converte o valor para ISO.

**Risco:** strings legadas como datas brasileiras não são necessariamente interpretáveis como timestamp pelo PostgreSQL/driver. Mesmo quando interpretáveis, a normalização para ISO elimina a representação textual original.

**Decisão recomendada:** não fazer conversão silenciosa na primeira migração. Preservar o valor original em campo textual próprio (por exemplo `data_legada_texto`) e, somente quando a interpretação for inequívoca e validada, preencher um campo temporal normalizado separado. Definir explicitamente fuso horário e regra de interpretação antes de converter. A solução deve manter compatibilidade com o contrato da API.

**Bloqueio:** não importar acertos para a coluna temporal atual até corrigir e testar esse contrato.

### 2.2 Atomicidade do registro de negócio e do mapa de origem

**Evidência no código:**
- `PostgresUnitOfWork` abre uma conexão pela fábrica e confirma ou reverte uma transação por contexto.
- Os repositórios atuais encapsulam operações individuais em suas próprias unidades de trabalho.
- `CollectionRepository` não oferece contexto transacional compartilhado entre repositórios.

**Risco:** executar `repository.add()` e depois gravar `migration_source_map` em outra conexão permite que o primeiro commit ocorra e o segundo falhe. Uma repetição poderia encontrar registro sem mapa de origem.

**Decisão recomendada:** implementar um serviço/importador transacional que receba uma única conexão/unidade de trabalho e execute, no mesmo commit, a gravação do registro de destino, o vínculo de origem e o evento de resultado. Não compor atomicidade chamando os repositórios atuais em sequência.

**Bloqueio:** a interface atual dos repositórios não basta, isoladamente, para garantir essa atomicidade.

### 2.3 Preservação de IDs

**Evidência no código:**
- Os métodos `add(item_id, item)` dos adaptadores PostgreSQL recebem ID externo e o inserem como chave primária.
- Os schemas de entidades expõem IDs como texto.
- O serviço/importador ainda precisa de uma entrada dedicada que não gere um novo ID.

**Decisão recomendada:** o importador deve validar e preservar o ID legado como string. Deve classificar colisão quando a chave já existir sem um vínculo de origem que comprove a identidade. Não usar o fluxo comum de criação se ele gerar IDs automaticamente.

### 2.4 Datas de cadastro de produtos

**Evidência no código:**
- `EstoqueInput.dataCadastro` aceita string vazia ou data estrita `AAAA-MM-DD`.
- O DDL usa `date null`.
- O adaptador converte data para ISO na leitura e grava string vazia como NULL.

**Decisão recomendada:** manter a regra estrita para o campo novo do Shadow, mas não aplicar essa validação diretamente sobre qualquer valor legado. Guardar o original e preencher `data_cadastro` somente se a conversão for válida e sem ambiguidade. Não inventar data para registros sem valor.

### 2.5 Estoque e histórico de movimentos

**Evidência no código:**
- O adaptador de estoque bloqueia a linha do produto durante edição e impede alterar saldo cadastral depois que existem movimentos.
- O repositório de acertos possui operação transacional específica que bloqueia produto e grava movimento/saldo no mesmo commit.
- O schema de movimento exige quantidade positiva e tipo Entrada/Saída.
- O legado permite situações históricas que diferem das regras atuais do Shadow, conforme fichas de migração anteriores.

**Decisão recomendada:** importar saldo inicial e histórico por fluxo especializado, com reconciliação explícita. Não simular cada movimento usando CRUD comum nem deixar o importador aplicar validações atuais como se fossem regras históricas do legado. Divergências e saldos negativos devem ser reportados e bloqueados para decisão, não corrigidos silenciosamente.

### 2.6 Financeiro e precisão decimal

**Evidência no código:**
- Schema valida `Decimal` com até 14 dígitos e 2 casas.
- SQL usa `numeric(14,2)`.
- Adaptador converte valor retornado para `Decimal`.
- Referência ao plano de contas é opcional no schema e nullable no SQL.

**Compatibilidade observada:** alinhamento estrutural entre schema, SQL e adaptador para o valor e o vínculo opcional.

**Cuidado de migração:** converter valores de origem usando Decimal a partir de representação textual/decimal confiável; não passar por float binário no cálculo do hash ou da transformação. Valores fora da precisão suportada devem ser classificados como inválidos, sem arredondamento automático.

### 2.7 Documentos e conteúdo Gzip

**Evidência no código:**
- Schema exige `arquivoCompactadoGzip` como string não vazia.
- SQL armazena o conteúdo em texto.
- O adaptador grava e lê a string sem transformação.
- A categoria é opcional e o texto da pasta permanece no registro.

**Compatibilidade observada:** armazenamento textual do conteúdo comprimido é coerente com preservação do payload Base64 legado.

**Decisão recomendada:** validar Base64/Gzip e hash do conteúdo descompactado antes de aplicar; preservar bytes/string original. Não mover para Storage nem recomprimir durante a migração. Categoria só recebe ID quando a correspondência por nome for exata e única; caso contrário, manter texto e vínculo nulo.

### 2.8 Vínculos de origem e constraints

O mapa de origem proposto usa referência polimórfica (`destination_schema` + `destination_table` + `destination_id`). PostgreSQL não consegue criar uma FK convencional que aponte dinamicamente para várias tabelas de negócio.

**Decisão recomendada:** manter a referência polimórfica validada pelo serviço de migração, criar unicidade/indexes para identidade de origem e destino e executar verificação pós-lote que confirme que cada destino existe. Se for desejada FK física, será necessário redesenhar o mapa por domínio ou adotar uma tabela central de identidades; não fingir que a referência polimórfica tem integridade referencial nativa.

## 3. Compatibilidades confirmadas nesta amostra

| Área | Resultado estático |
|---|---|
| ID de negócio como texto | Compatível com preservação de IDs legados |
| Financeiro Decimal / numeric(14,2) | Alinhado |
| Financeiro sem plano de contas | Suportado por FK nullable |
| Produto: marca, linha, fabricante | Presentes no schema, SQL e adaptador |
| Produto: dataCadastro | Tipo compatível para datas ISO válidas; legado requer preservação separada |
| Documentos Gzip em texto | Adaptador não transforma o conteúdo |
| Movimentos de estoque | Há fluxo transacional especializado; requer importador próprio |
| Controle de migração | Ainda não implementado no backend nem no banco |

## 4. Requisitos para a próxima implementação

1. Definir representação dual para datas históricas: valor original e valor normalizado opcional.
2. Criar abstração transacional de importação com conexão compartilhada.
3. Implementar inserção de IDs preservados sem gerador de ID.
4. Definir algoritmo/versionamento de hash canônico por tipo, incluindo Decimal, datas e strings.
5. Implementar mapa de origem com unicidade e tratamento de colisões.
6. Garantir evento e mapa consistentes com a transação de destino.
7. Criar importador específico de estoque que não viole a imutabilidade dos movimentos.
8. Criar validação Gzip/Base64 sem reescrita do conteúdo.
9. Especificar testes com dados sintéticos: reexecução do mesmo lote, falha entre gravações, colisão de ID, data pt-BR, data inválida, Decimal limite, referência órfã, Gzip corrompido e reconciliação de saldo.
10. Resolver desenho de role/RLS antes de executar qualquer migration local.

## 5. Próxima etapa segura

Produzir uma especificação técnica do contrato transacional do importador e do tratamento de datas históricas. Em seguida, implementar testes unitários com dados sintéticos, sem conexão PostgreSQL e sem tocar nos dados do Bravo original.

**Conclusão:** o desenho de controle de lotes é viável, mas não deve virar SQL executável ainda. O maior bloqueio funcional identificado nesta amostra é a divergência de tipo/formato das datas de acertos; o maior bloqueio arquitetural é a falta de uma transação compartilhada entre destino, mapa de origem e eventos.
