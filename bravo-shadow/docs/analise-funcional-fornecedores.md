# Análise funcional — Fornecedores

Data: 2026-11-27  
Escopo: inspeção estática do fluxo legado, schemas, service, router, autorização e adapter PostgreSQL Shadow.

## Fluxo legado identificado

A tela `renderFornecedoresView` apresenta tabela com CNPJ, Razão Social e ações de editar/excluir. O modal possui somente dois campos obrigatórios: CNPJ e Razão Social. Não foram identificados campos de contato, endereço, inscrição estadual ou dados bancários neste fluxo; não inventar campos adicionais.

## Contrato backend Shadow

- `GET /api/v1/fornecedores` — `fornecedores:read`.
- `POST /api/v1/fornecedores` — `fornecedores:create`.
- `PUT /api/v1/fornecedores/{id}` — `fornecedores:update`.
- `DELETE /api/v1/fornecedores/{id}` — `fornecedores:delete`.

Schema: `cnpj` e `razaoSocial` obrigatórios; strings aparadas; campos extras recusados. Admin e Operador possuem CRUD no catálogo de capacidades.

## Persistência

`PostgresFornecedoresRepository` usa `bravo_shadow.fornecedores`, colunas `id, cnpj, razao_social`. Na atualização incrementa `version`, mas o router não exige If-Match/ETag. Storage usa PostgreSQL somente quando selecionado explicitamente; o padrão memória é volátil. Nenhuma base foi conectada ou migration aplicada.

## Interface criada

- Formulário CNPJ/Razão Social.
- Pesquisa prevista por CNPJ ou razão social.
- Tabela com colunas do legado e espaço para ações.
- Avisos de integridade e permissões.
- Estado vazio sem dados fictícios.

Todos os controles estão desabilitados. A tela não executa requests nem consulta ou altera dados até integração Google/Bearer e API HTTPS isolada.

## Lacunas e riscos

1. Schema aceita string não vazia, sem validar formato ou dígitos verificadores do CNPJ.
2. Service não detecta CNPJ duplicado; não há unicidade demonstrada no adapter consultado.
3. Exclusão física sem verificação de vínculos em compras, financeiro ou outros módulos.
4. Versionamento interno não está protegido por If-Match/ETag no router.
5. Operador possui criar, editar e excluir; confirmar se é a matriz operacional desejada.
6. Listagem retorna coleção inteira, sem filtros/paginação server-side.
7. Não foi identificada auditoria transacional de negócio específica para CRUD.
8. Não ampliar o contrato com contato/endereço/dados bancários sem confirmação do legado.

## Próximos passos

1. Definir validação CNPJ e normalização compatível com registros existentes.
2. Adicionar índice único e tratamento HTTP 409 para duplicidade.
3. Definir bloqueio por vínculos e política de inativação/exclusão.
4. Expor If-Match/ETag e auditoria transacional.
5. Revisar permissões de Operador.
6. Acrescentar filtros/paginação conforme volume.
7. Integrar Google/Bearer e homologar somente com dados sintéticos.

## Situação

- [x] Campos e ações legados identificados.
- [x] Schema, rotas, capacidades e adapter PostgreSQL inspecionados.
- [x] Tela Shadow criada sem dados fictícios nem chamadas.
- [x] README e matriz atualizados.
- [ ] Validação e unicidade de CNPJ.
- [ ] Política de vínculos/exclusão.
- [ ] Concorrência, auditoria e permissões.
- [ ] Integração Google/Bearer e homologação.

**Status: estrutura cadastral mapeada; operações bloqueadas até validação fiscal, integridade referencial, auditoria e autenticação.**
