# Ficha técnica de coleções — Fase 0 (lote 01)

## Objetivo e limites

Comparar, somente por leitura de código, os três primeiros domínios da migração: **Condomínio**, **Conselho** e **Plano de Contas**. Esta ficha registra o comportamento observado no legado e os contratos atuais do Shadow. Não representa aprovação de regras novas nem autorização para extrair dados reais.

## Baseline

- Legado: branch `upgrade/project-hardening`, arquivo `index.html`.
- SHA do legado observado nesta revisão: `873dbf37bbcf2082faa0444ac28cb9ca9f8ff21c`.
- Shadow: branch `bravo-shadow`.
- Persistência legada observada: objeto JSON agregado em `public.condominio_dados`, registro `id='principal'`, coluna `payload`; cache local em `guardioes_bravo_db`.
- A amostra `DEFAULT_DATA` contém dados demonstrativos e **não deve ser importada**.

## 1. Condomínio

### Legado — observado

A propriedade `db.condominio` é um objeto único. O objeto inicial contém:

| Campo | Tipo observado | Uso/observação |
|---|---|---|
| `nome` | texto | Nome do condomínio |
| `cnpj` | texto | Identificação cadastral |
| `razaoSocial` | texto | Presente no objeto inicial; não aparece no formulário de edição inspecionado |
| `endereco` | texto | Presente no objeto inicial; não aparece no formulário de edição inspecionado |
| `bairro` | texto | Presente no objeto inicial; não aparece no formulário de edição inspecionado |
| `cidade` | texto | Presente no objeto inicial; não aparece no formulário de edição inspecionado |
| `uf` | texto | Presente no objeto inicial; não aparece no formulário de edição inspecionado |
| `cep` | texto | Presente no objeto inicial; não aparece no formulário de edição inspecionado |
| `telefone` | texto | Formulário de edição |
| `email` | texto | Formulário de edição |
| `copelBloco1` a `copelBloco4` | texto | Números de instalação por bloco |
| `copelAreasComuns` | texto | Número de instalação das áreas comuns |
| `gasSalao` | texto | Registro/medidor de gás do salão |
| `sanepar` | texto | Matrícula de água |

O formulário renderizado permite editar nome, CNPJ, telefone, e-mail e os sete identificadores de concessionárias. A função de gravação observada atualiza esses campos no objeto e salva o payload. Os campos cadastrais de razão social e endereço continuam presentes no objeto inicial, mas **não são editáveis por esse formulário específico**.

### Shadow — observado

- Schema `CondominioPatch` aceita os 17 campos acima como texto opcional e rejeita propriedades extras.
- Strings são aparadas com `strip()`.
- API: `GET /api/v1/condominio` e `PUT /api/v1/condominio`.
- O contrato é um objeto único, não uma coleção com IDs por registro.

### Mapeamento preliminar

- Chave de origem: `payload.condominio`.
- Destino lógico: registro único de condomínio no domínio `condominio`.
- Preservar todos os campos, inclusive os que não aparecem no formulário legado atual.
- Não preencher campos ausentes com os valores demonstrativos do `DEFAULT_DATA`.
- Não normalizar CNPJ, CEP, telefone ou identificadores de concessionárias sem regra aprovada.

### Pendências e critérios de aceite

1. Confirmar no histórico/uso real se razão social e endereço são dados operacionais mantidos por outro fluxo ou apenas campos antigos.
2. Definir política para campos nulos, ausentes e strings vazias sem apagar valores existentes acidentalmente.
3. Testar round-trip: importar objeto → consultar → atualizar somente um campo → confirmar que os demais permanecem iguais.
4. Reconciliar quantidade: exatamente um objeto de condomínio esperado por snapshot válido.
5. Confirmar que nenhum campo é descartado pelo serializador ou pela tabela destino.

## 2. Conselho

### Legado — observado

A coleção `db.conselheiros` é uma lista. O formulário de inclusão/edição trabalha com:

| Campo | Tipo observado | Regra observada |
|---|---|---|
| `id` | texto | Mantido na edição; novo ID usa prefixo `cons_` e timestamp |
| `nome` | texto | Obrigatório no formulário |
| `cargo` | texto | Obrigatório no formulário; novo registro inicia com sugestão `Síndico` |
| `BlocoAp` | texto | Opcional; nome da propriedade tem maiúsculas internas |
| `telefone` | texto | Opcional |

A tela lista nome, cargo e bloco/apartamento. A edição inclui telefone. Há operações de criar, editar e excluir. A exclusão é acionada pelo helper genérico do legado; o comportamento completo desse helper ainda precisa ser validado antes de reproduzir regras de exclusão.

### Shadow — observado

- Schema `ConselheiroInput`: `nome`, `cargo`, `BlocoAp` e `telefone`; ID é acrescentado no modelo de saída.
- `nome` e `cargo` têm comprimento mínimo de 1; strings são aparadas.
- API: `GET /api/v1/conselheiros`, `POST /api/v1/conselheiros`, `PUT /api/v1/conselheiros/{item_id}` e `DELETE /api/v1/conselheiros/{item_id}`.

### Mapeamento preliminar

- Chave de origem: `payload.conselheiros[]`.
- Destino lógico: coleção `conselheiros`.
- Preservar o ID original quando válido e único; não regenerar IDs durante a carga inicial.
- Preservar exatamente a propriedade `BlocoAp` até uma decisão explícita de versionamento/renomeação do contrato.
- Não converter telefone para formato numérico; preservar como texto.

### Pendências e critérios de aceite

1. Auditar o helper legado de exclusão e confirmar se há logs ou referências indiretas.
2. Verificar IDs duplicados, ausentes e tipos inesperados no snapshot.
3. Confirmar se há outras propriedades históricas nos registros além das quatro observadas.
4. Testar round-trip de todos os campos, inclusive telefone e `BlocoAp`.
5. Confirmar contagem de registros e relatório de IDs rejeitados/duplicados.

## 3. Plano de Contas

### Legado — observado

A coleção `db.plano_contas` é uma lista com os campos:

| Campo | Tipo observado | Regra observada |
|---|---|---|
| `id` | texto | Exemplos usam prefixo `pc_`; novos IDs usam prefixo e timestamp |
| `codigo` | texto | Campo obrigatório no formulário |
| `nome` | texto | Campo obrigatório no formulário |
| `tipo` | texto enumerado | Opções visíveis: `Receita` e `Despesa`; novo registro inicia como `Despesa` |

A tela apresenta código, nome e tipo. Permite criar, editar e excluir. Lançamentos financeiros procuram a conta pelo valor de `planoContaId`; quando não encontram correspondência, a interface apresenta a conta como não vinculada. Isso confirma uma referência por ID no consumo financeiro, mas não prova que todos os registros legados tenham referência válida.

### Shadow — observado

- Schema `PlanoContaInput`: `codigo` (1–30), `nome` (2–160) e `tipo` limitado a `Receita` ou `Despesa`; espaços externos são removidos e valores em branco são rejeitados.
- Modelo de saída inclui `id` e `version`.
- API: `GET /api/v1/plano-contas`, `POST /api/v1/plano-contas`, `PUT /api/v1/plano-contas/{item_id}` e `DELETE /api/v1/plano-contas/{item_id}`.
- Criação/edição devolve ETag; atualização exige `If-Match` para controle de versão.
- A camada de serviço/repositório do Shadow já trata referência financeira ao excluir conta com vínculo, usando restrição de integridade (confirmar com teste de integração PostgreSQL antes de considerar validado em banco real).

### Mapeamento preliminar

- Chave de origem: `payload.plano_contas[]`.
- Destino lógico: coleção `plano_contas`.
- Preservar IDs e códigos como texto; não converter códigos como `1.1` para número.
- Mapear referências financeiras usando `financeiro[].planoContaId` → `plano_contas[].id`.
- Não inferir hierarquia contábil a partir dos pontos no código. A estrutura hierárquica não está comprovada.

### Pendências e critérios de aceite

1. Fazer inventário de todos os valores distintos de `tipo` no conjunto autorizado; rejeitar valores desconhecidos para análise, não convertê-los silenciosamente.
2. Verificar duplicidade de ID e de código; não impor unicidade de código sem confirmar regra de negócio.
3. Identificar lançamentos financeiros com `planoContaId` ausente, vazio ou sem correspondência.
4. Confirmar comportamento legado ao excluir conta já utilizada.
5. Ensaiar atualização concorrente via ETag e exclusão com referência em banco PostgreSQL local.
6. Reconciliar contagens, IDs e vínculos antes/depois da carga.

## 4. Riscos transversais identificados neste lote

- **Campos não editáveis no formulário:** o objeto legado de Condomínio contém dados cadastrais que não são expostos no formulário inspecionado. Uma migração não pode descartá-los apenas porque não aparecem na tela.
- **Identificadores:** IDs legados são strings; preservar para manter vínculos e rastreabilidade.
- **Nomes de campo:** `BlocoAp` é sensível a maiúsculas/minúsculas em JSON e no contrato atual.
- **Referências financeiras:** Plano de Contas é dependência do Financeiro; não migrar Financeiro sem resolver todas as referências.
- **Exclusões:** não reproduzir exclusão em cascata ou remoção física até confirmar comportamento legado e regra aprovada.
- **Demonstração versus produção:** exemplos de `DEFAULT_DATA` são apenas defaults demonstrativos; não são amostra de produção.

## 5. Sequência recomendada para este lote

1. Completar auditoria de exclusão do legado para Conselho e Plano de Contas.
2. Obter futuramente um snapshot sintético/anonimizado autorizado e validar o formato, sem conectar o Shadow à base de produção.
3. Executar validador somente de leitura para IDs, campos, enums e referências.
4. Definir relatório de rejeições e resolução manual; nunca descartar silenciosamente.
5. Testar importação idempotente em PostgreSQL local descartável.
6. Só então considerar estes domínios prontos para um piloto controlado.

## 6. Evidências consultadas

- Legado `index.html`: inicialização `DEFAULT_DATA`, `renderCondominioView`, `salvarDadosCondominio`, `renderModalConselheiro`, `salvarModalConselheiro`, `renderPlanoContasView`, `renderModalPlanoConta` e `salvarModalPlanoConta`.
- Shadow:
  - `backend/app/modules/condominio/schemas.py` e `router.py`.
  - `backend/app/modules/conselheiros/schemas.py` e `router.py`.
  - `backend/app/modules/plano_contas/schemas.py` e `router.py`.

**Limite desta entrega:** leitura de código e documentação apenas. Nenhuma carga, migração, alteração no banco, mudança de API, alteração de interface ou edição do legado foi realizada. Os testes de integração ainda não foram executados.
