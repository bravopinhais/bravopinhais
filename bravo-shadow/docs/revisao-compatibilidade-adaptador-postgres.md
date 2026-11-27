# Revisão de compatibilidade: adaptador PostgreSQL de importação

**Estado:** revisão estática dos rascunhos; não é aprovação para executar SQL.

## Escopo conferido

Foram comparados os identificadores e campos de:

- `backend/app/core/migration_apply_store_postgres.py`
- `backend/app/core/migration_source_records_postgres.py`
- `backend/app/core/migration_apply_authorization_postgres.py`
- `docs/sql-piloto-financeiro.sql`
- `docs/sql-estoque-compras-consumo-rascunho.sql`
- `docs/sql-controle-lotes-importacao-rascunho.sql`
- `docs/sql-execucao-aprovacao-apply-rascunho.sql`
- `docs/sql-auditoria-rascunho.sql`

## Compatibilidade observada

1. As 15 coleções de destino presentes em `TARGET_COLUMNS` correspondem aos nomes de tabelas e colunas declarados no rascunho funcional `sql-piloto-financeiro.sql`, incluindo os identificadores camelCase entre aspas (`razaoSocial`, `copelBloco1` e `BlocoAp`).
2. A evolução de estoque acrescenta colunas já contempladas pelo allowlist: `setor`, `unidade`, `valor_unitario`, `status`, `cor` e `foto_path`. A precisão de quantidade é ampliada para três casas decimais.
3. A proveniência usa `first_batch_id`, conforme o DDL; o adaptador não tenta gravar uma coluna `batch_id` inexistente nessa tabela.
4. A consulta de autorização lê os campos presentes nos rascunhos de lotes, execução e aprovação, mantendo a ordem de bloqueio lote → execução → aprovação.
5. O INSERT de auditoria usa as oito colunas declaradas em `sql-auditoria-rascunho.sql`.

## Correção aplicada

O adaptador agora declara `REQUIRED_TARGET_COLUMNS`, espelhando os campos `NOT NULL` sem default das tabelas funcionais. Antes de montar/executar o INSERT, rejeita payload incompleto. Campos opcionais ou com default continuam omitíveis; `condominio` não exige campos além do ID, pois as demais colunas têm default.

Também foi incluído teste estático/sintético para garantir que os campos obrigatórios pertençam ao allowlist e que payloads incompletos sejam recusados antes de qualquer acesso ao cursor.

## Limitações e bloqueios restantes

- Os arquivos SQL continuam sendo rascunhos explicitamente não executáveis; nenhum foi aplicado.
- Esta conferência é estática. Não substitui parsing PostgreSQL, criação de schema descartável, inspeção de catálogo (`information_schema`) ou teste transacional real.
- Os tipos Python dos valores ainda precisam ser validados contra os tipos SQL no limite de entrada do importador; a validação de campos obrigatórios não faz coerção de datas, decimais ou enums.
- A lista de coleções e campos precisa ser revisada novamente quando o DDL virar migration versionada.
- Não foram concedidos privilégios, criadas policies, abertas conexões ou gravados dados.

## Próxima barreira

Antes de homologação PostgreSQL, consolidar os rascunhos em migrations locais revisadas, provisionar banco descartável isolado e validar schema/tipos/constraints e rollback com dados exclusivamente sintéticos. Nenhuma dessas ações está autorizada ou executada por este commit.
