# Ficha técnica — coleções da Fase 0 (lote 05)

**Escopo:** Estoque, Acertos de Estoque e Motivos de Acerto.  
**Branch:** `bravo-shadow`  
**Fonte legada consultada:** `index.html` na branch `bravo-shadow` (SHA `873dbf37bbcf2082faa0444ac28cb9ca9f8ff21c`).  
**Objetivo:** inventário e equivalência; não executa migração de dados.

## 1. Estoque — coleção legada `db.estoque[]`

A gravação legada constrói o objeto com os campos:

| Campo legado | Uso observado |
|---|---|
| `id` | Identificador; edição preserva o ID existente; criação usa `est_ + Date.now()`. |
| `item` | Descrição do produto. |
| `quantidade` | Saldo atual. A interface também tolera legado alternativo `qtd` em leituras. |
| `minimo` | Limite inferior para classificação visual. |
| `maximo` | Limite superior para classificação visual. |
| `etiqueta` | Código / código de barras. |
| `fotoNome` | Nome original do arquivo de imagem. |
| `fotoCompactadaGzip` | Conteúdo da imagem codificado em Base64 após compactação Gzip. |

A foto é descompactada com `pako.inflate`; o MIME é inferido pela extensão de `fotoNome`. A exportação CSV remove `fotoCompactadaGzip`, mas o backup JSON geral serializa o objeto completo. A migração deve preservar o conteúdo Base64 integral e o nome original, sem decodificar/recompactar, truncar ou normalizar os bytes.

**Campos adicionais existentes somente no Shadow:** `marca`, `linha`, `fabricante`, `dataCadastro`. Eles foram acrescentados para rastreabilidade e não foram encontrados na gravação do objeto legado consultada. Não preencher retroativamente com valores inventados; manter vazio/nulo conforme o contrato Shadow.

### Equivalência Shadow

- Schema: `backend/app/modules/estoque/schemas.py`.
- API: `GET/POST /api/v1/estoque`, `PUT/DELETE /api/v1/estoque/{item_id}`.
- Serviço: IDs novos gerados como `est_shadow_...`; a criação normal não aceita ID legado.
- PostgreSQL: `bravo_shadow.estoque`, incluindo os campos de foto e os quatro campos adicionais.

**Regra obrigatória de importação:** criar caminho administrativo de carga que preserve o ID original e os campos exatamente; não usar o POST comum para importar registros históricos.

## 2. Acertos — coleção legada `db.acertos_estoque[]`

A função de gravação cria:

| Campo | Significado observado |
|---|---|
| `id` | Identificador `ac_ + Date.now()`. |
| `data` | Data/hora formatada com `toLocaleString('pt-BR')`. |
| `tipo` | `Entrada` ou `Saída`. |
| `produtoId` | Referência ao `id` do produto em `db.estoque[]`. |
| `quantidade` | Quantidade movimentada, positiva na entrada e na saída. |
| `motivo` | Texto selecionado no cadastro de motivos; o legado não grava ID do motivo. |

O saldo do produto é atualizado na mesma operação lógica do navegador, antes de adicionar o registro ao array. O histórico exibe o produto resolvendo `produtoId` contra o estoque atual. Se o produto não existir, exibe “Produto eliminado”.

### Diferenças de comportamento que exigem decisão

1. **Saída maior que o saldo:** legado pede confirmação e, se confirmada, permite saldo negativo. O Shadow rejeita a operação com HTTP 409. Não converter movimentos históricos nem impor retroativamente o bloqueio sem contabilizar saldos negativos já existentes.
2. **Exclusão de acerto:** legado permite excluir o registro do histórico sem reverter o saldo do produto. O Shadow rejeita exclusão/alteração de movimentos (HTTP 409) e orienta movimento compensatório. Preservar os registros históricos; não executar exclusões como parte da migração.
3. **Data:** legado guarda texto local em formato pt-BR; Shadow cria timestamp ISO com fuso. Não interpretar automaticamente todo texto legado como UTC. Preservar o texto original em campo de origem ou metadado de migração e definir conversão somente após validar formatos reais.
4. **Motivo:** legado grava apenas o nome/texto. O Shadow admite `motivoId` opcional e mantém `motivo` textual. Associar um ID somente quando houver correspondência inequívoca; caso contrário, preservar o texto e deixar `motivoId` nulo.
5. **Integridade referencial:** o legado pode manter acerto apontando para produto posteriormente eliminado. O Shadow/PostgreSQL modela referência ao produto e impede remoção referenciada. Identificar órfãos antes da carga; não descartá-los nem inventar produto.

### Equivalência Shadow

- Schema: `backend/app/modules/acertos_estoque/schemas.py`.
- API: `GET/POST /api/v1/acertos-estoque`; não oferece edição; exclusão responde conflito.
- Serviço: valida produto, valida motivo quando `motivoId` informado, calcula delta e registra movimento.
- PostgreSQL: `bravo_shadow.acertos_estoque`; `PostgresAcertosEstoqueRepository.register_movement()` bloqueia o produto com `FOR UPDATE`, atualiza saldo e insere o movimento na mesma transação.

O serviço em memória atualiza saldo e histórico em duas operações separadas; a atomicidade descrita acima é do adaptador PostgreSQL. Nenhuma dessas rotinas foi testada contra banco real nesta etapa.

## 3. Motivos — coleção legada `db.motivos_acerto_estoque[]`

Estrutura observada: `{ id, nome }`. Os registros iniciais definidos em `DEFAULT_DATA` são apenas valores padrão do código, não evidência de dados efetivamente existentes em produção. O carregamento legado repõe essa lista padrão quando a coleção está ausente no cache/payload. Portanto, **não importar DEFAULT_DATA como se fosse conteúdo real**.

Na interface, o formulário de acerto apresenta o nome do motivo e grava somente esse texto em `ac.motivo`. A exclusão de um motivo remove o cadastro do array sem verificar acertos anteriores; por isso, o texto histórico é a única informação estável do motivo em registros legados.

### Equivalência Shadow

- Módulo: `backend/app/modules/motivos_acerto`.
- API: `GET/POST /api/v1/motivos-acerto-estoque`; não há edição.
- Schema: `id`, `nome`.
- Serviço: IDs novos gerados como `mot_shadow_...`; exclusão consulta referências por `motivoId`.
- O importador deve preservar IDs legados dos motivos quando importar o cadastro e só preencher `motivoId` nos acertos quando a associação textual for inequívoca.

## 4. Ordem de migração e validações

Ordem proposta, sujeita à conferência do inventário real:

1. Importar produtos preservando IDs, quantidades, limites, etiquetas e dados Gzip.
2. Importar motivos preservando IDs e nomes; distinguir dados reais de valores padrão inseridos pelo fallback legado.
3. Importar acertos preservando IDs, data textual original, tipo, produtoId, quantidade e motivo textual.
4. Resolver referências de produto e motivo; produzir relatório de órfãos e ambiguidades sem descartá-los.
5. Reconciliar saldo: comparar saldo atual de cada produto com a quantidade inicial mais entradas menos saídas. A divergência pode decorrer de exclusões legadas de acertos, movimentos acima do saldo ou alterações diretas no cadastro.
6. Somente após reconciliação, habilitar fluxo normal de movimentos no Shadow.

### Critérios de aceite da futura carga

- Contagem por coleção antes/depois igual, com exceções documentadas.
- IDs originais preservados e sem colisões.
- Hash/bytes dos conteúdos Gzip preservados integralmente.
- Datas legadas preservadas sem conversão ambígua.
- Relatório explícito de referências órfãs, motivos sem correspondência e saldos divergentes.
- Nenhum registro de `DEFAULT_DATA` tratado como dado de produção sem evidência.
- Nenhum acerto histórico editado ou excluído durante a carga.
- Saldo final reconciliado por produto, com diferenças explicadas e aprovadas.

## 5. Limites desta inspeção

Foi feita leitura estática do `index.html` e dos schemas, routers, services, adaptadores e wiring de armazenamento do Shadow. Não houve extração de payload real, consulta a banco, execução de testes, migração, alteração de código funcional ou validação visual em navegador. Os dados reais, formatos históricos de data e quantidade de registros continuam desconhecidos.

**Conclusão:** o Shadow cobre as entidades centrais, mas a migração exige importação que preserve IDs e conteúdo binário, tratamento de órfãos, compatibilidade das datas e reconciliação dos saldos antes de qualquer cutover.
