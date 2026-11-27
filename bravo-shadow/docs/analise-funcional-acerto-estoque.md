# Análise funcional — Acerto de Estoque

Data da inspeção: 27/11/2026
Escopo: comparação estática do módulo legado com a branch bravo-shadow.

## 1. Legado observado

O histórico exibe data/hora, tipo, produto, quantidade, motivo e ação para excluir. O formulário permite escolher Entrada ou Saída, localizar produto por etiqueta/nome, informar quantidade e selecionar motivo. A rotina legada altera o saldo do produto e insere o registro do acerto. A exclusão legada remove apenas o registro de histórico, sem recompor o saldo, podendo produzir divergência entre saldo e movimentos.

## 2. Contrato Shadow

### Schema

AcertoInput contém tipo (Entrada/Saída), produtoId obrigatório, quantidade Decimal positiva com até três casas, motivo obrigatório e motivoId opcional. Strings obrigatórias são aparadas. Campos extras são recusados. Data/hora e identificador são atribuídos pelo serviço.

### API

- GET /api/v1/acertos-estoque — acertos_estoque:read.
- POST /api/v1/acertos-estoque — acertos_estoque:create.
- GET /api/v1/motivos-acerto-estoque — motivos_estoque:read.

Admin e Operador têm leitura e criação de movimentos no catálogo de capacidades. Não existem rotas PUT/DELETE para acertos.

## 3. Regras do serviço

O serviço recupera o produto e, se motivoId for informado, resolve o nome no catálogo de motivos. Entrada soma a quantidade; Saída subtrai. Saída superior ao saldo retorna HTTP 409. O caminho PostgreSQL delega ao repositório de movimentos, que bloqueia a linha do produto com SELECT FOR UPDATE, verifica saldo não negativo, atualiza produto e insere movimento dentro da mesma unidade transacional. Falha na gravação reverte o conjunto.

O serviço possui método de exclusão que sempre rejeita a operação com HTTP 409, orientando movimento compensatório. O router não expõe rota de exclusão. Assim, o histórico fica imutável pela API.

## 4. Interface adicionada

A função acertoEstoqueView() foi adicionada à navegação Shadow com formulário para tipo, produto, quantidade e motivo, e tabela histórica com data/hora, tipo, produto, quantidade e motivo. A interface descreve as invariantes e não oferece ações de edição ou exclusão.

Os controles permanecem desabilitados, sem chamadas de rede e sem dados fictícios, até integração Google/Bearer e API HTTPS isolada.

## 5. Lacunas

1. Formulário e histórico ainda não carregam os catálogos nem chamam a API.
2. Listagem não possui filtros/paginação e a busca do produto não foi integrada.
3. Scanner, anexos/evidências e fluxo de aprovação não foram identificados no contrato Shadow.
4. Auditoria explícita do movimento não foi confirmada na mesma transação.
5. O caminho em memória atualiza saldo e histórico em operações separadas; a garantia atômica descrita vale para o adapter PostgreSQL. Não ativar memória como persistência de produção.
6. O legado permitia excluir movimento sem recompor saldo. Esse comportamento é inseguro e não foi replicado.

## 6. Critérios para habilitação

- Integrar autenticação Google validada e token Bearer a API HTTPS isolada.
- Carregar produtos e motivos de forma autenticada, com pesquisa e paginação.
- Confirmar auditoria transacional e trilha de autor para cada movimento.
- Garantir backend PostgreSQL e unidade transacional ativa antes de liberar criação.
- Manter movimentos imutáveis; corrigir somente por movimento compensatório autorizado.

## 7. Limites

Entrega de interface e documentação. Nenhum teste executado, SQL aplicado, banco conectado, deploy/publicação ou alteração em main/dados de produção.