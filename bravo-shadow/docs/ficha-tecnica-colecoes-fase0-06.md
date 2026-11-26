# Ficha técnica — coleções da Fase 0 (lote 06)

**Escopo:** Gestão de Documentos e vínculo com Pastas/Categorias.  
**Branch:** `bravo-shadow`  
**Fonte legada consultada:** `index.html` na branch `bravo-shadow` (SHA `873dbf37bbcf2082faa0444ac28cb9ca9f8ff21c`).  
**Objetivo:** inventário e equivalência; não executa migração de dados.

## 1. Documentos — coleção legada `db.documentos[]`

O objeto gravado pelo formulário legado contém:

| Campo | Significado observado |
|---|---|
| `id` | Identificador; criação usa `doc_ + Date.now()`; edição preserva o ID. |
| `pasta` | Nome textual da pasta/categoria selecionada. |
| `titulo` | Título informado pelo usuário. |
| `nomeArquivo` | Nome original do arquivo; se não houver arquivo novo na edição, preserva o nome anterior; em criação, fallback `doc.pdf`. |
| `arquivoCompactadoGzip` | Conteúdo do arquivo em Base64 após compactação com Pako/Gzip. |

O formulário de criação exige arquivo; na edição, permite manter o arquivo anterior. A rotina de compactação lê os bytes originais, aplica `pako.deflate` e armazena Base64. As rotinas de visualização e download usam `pako.inflate` para recuperar os bytes. O documento deve ser tratado como conteúdo binário, não como texto UTF-8.

**Preservação obrigatória:** manter o Base64 e os bytes comprimidos exatamente como recebidos, além de `nomeArquivo`; não recompactar, converter para texto, remover caracteres, truncar ou deduzir MIME apenas pelo título. Validar amostras com hash do conteúdo descompactado antes/depois da carga.

## 2. Pastas/Categorias — coleção legada `db.categorias[]`

Estrutura observada: `{ id, nome }`. A tela de documentos monta a lista de seleção a partir dos nomes em `db.categorias[]`; se não houver categorias cadastradas, apresenta opções de fallback `Geral`, `Assembleias`, `Financeiro`, `Manutenção`.

O documento legado guarda somente `pasta` (texto), não guarda `categoriaId`. A relação é, portanto, textual e pode ficar ambígua se existirem categorias com nomes repetidos, se o nome tiver sido alterado ou se a categoria tiver sido excluída. Não existe prova de FK entre as duas coleções no legado.

A tela de categorias permite excluir categorias sem uma verificação visível de documentos vinculados. Assim, documentos antigos podem conter nomes de pasta que já não existem na coleção de categorias.

## 3. Equivalência Shadow

### Documentos

- Schema: `backend/app/modules/documentos/schemas.py`.
- Campos: `id`, `pasta`, `categoriaId` opcional, `titulo`, `nomeArquivo`, `arquivoCompactadoGzip`.
- API: `GET/POST /api/v1/documentos`, `GET/PUT/DELETE /api/v1/documentos/{item_id}`.
- Serviço: cria IDs `doc_shadow_...`; quando `categoriaId` é informado, valida a categoria e deriva `pasta` do nome atual da categoria.
- PostgreSQL: `bravo_shadow.documentos`; o adaptador persiste `pasta`, `categoria_id`, `titulo`, `nome_arquivo` e `arquivo_compactado_gzip`.
- A exclusão de categoria é protegida por verificação no serviço e pela integridade referencial no PostgreSQL.

### Categorias

- Schema: `backend/app/modules/categorias/schemas.py`.
- Campos: `id`, `nome`.
- Serviço Shadow gera IDs `cat_shadow_...`; a criação comum não aceita ID legado.
- A exclusão é bloqueada quando existem documentos vinculados por `categoriaId`.

**Diferença essencial:** Shadow possui relação opcional por ID; legado possui apenas texto. O importador não deve inventar `categoriaId` a partir de uma correspondência aproximada. A associação só pode ser criada quando o nome corresponder de forma única e a política de migração aprovar a conversão. Caso contrário, preservar `pasta` exatamente e deixar `categoriaId` nulo.

## 4. Regras para a futura migração

1. Importar categorias preservando IDs e nomes originais.
2. Importar documentos preservando IDs, título, pasta textual, nome original do arquivo e Base64 Gzip integral.
3. Resolver `pasta` → `categoriaId` somente quando houver uma única categoria com correspondência exata, sem normalização destrutiva.
4. Para pasta sem categoria correspondente, preservar o texto e registrar pendência; não criar categoria automaticamente sem regra aprovada.
5. Para nomes duplicados, não escolher arbitrariamente: manter `categoriaId` nulo e gerar relatório de ambiguidade.
6. Para documentos sem arquivo, Base64 inválido ou arquivo que não descompacta, preservar o registro e isolar a ocorrência para análise; não descartar nem substituir por arquivo vazio.
7. Testar a integridade por amostragem e por hash: comparar tamanho/hash dos bytes descompactados no legado e no Shadow.
8. Não misturar opções de fallback da interface com categorias reais. Valores padrão exibidos quando a lista está vazia não são, por si só, dados de produção.
9. Confirmar a política de exclusão e retenção documental antes de liberar exclusão no sistema migrado.

## 5. Riscos e pontos em aberto

- A referência por nome pode ter ficado órfã ou ambígua ao longo do tempo.
- O legado não fornece `categoriaId`; vínculo automático só é seguro em correspondência única.
- O campo Gzip pode conter arquivos de qualquer tipo, não apenas PDF; a extensão original é preservada em `nomeArquivo`.
- O inventário estático não revela tamanho total, limites de arquivo, duplicidade de conteúdo ou integridade de todos os Base64 armazenados.
- O Shadow aceita `categoriaId` opcional, mas não há mecanismo documentado de armazenamento externo; o conteúdo permanece no banco.
- O router Shadow expõe DELETE de documento. A política de retenção e trilha de auditoria deve ser aprovada antes de ativar essa operação em ambiente acessível.
- A migração precisa preservar o ID legado por caminho administrativo específico; o POST comum gera ID novo.

## 6. Limites desta inspeção

Foi feita leitura estática do `index.html` e dos schemas, routers, services e adaptadores Shadow. Não houve extração de payload real, leitura de banco, verificação de hashes de arquivos reais, execução de testes, migração ou alteração funcional. O número, tamanho e integridade dos documentos reais permanecem desconhecidos.

**Conclusão:** documentos e categorias estão representados no Shadow, mas a relação mudou de texto para referência opcional por ID. A carga deve preservar o texto e os bytes originais, resolver vínculos somente quando inequívocos e manter relatório de órfãos/ambiguidades.
