# Auditoria de Estoque & Inventário e Acertos

## Fonte e preservação
Inspeção estática de `index.html` na branch `upgrade/project-hardening`, SHA `873dbf37bbcf2082faa0444ac28cb9ca9f8ff21c`. O original não foi modificado.

## Cadastro de produtos (`db.estoque`)
Campos efetivamente gravados pelo formulário:
- `id`: `est_` + timestamp.
- `item`: descrição, obrigatória.
- `quantidade`: inteiro; novo item inicia em 1; valor inválido/vazio vira 0 ao salvar.
- `minimo`: inteiro; default 0.
- `maximo`: inteiro; default visual 10, mas o salvamento usa 0 se vazio/inválido.
- `etiqueta`: código/código de barras, opcional.
- `fotoNome` e `fotoCompactadaGzip`: nome e conteúdo da foto compactada.

O formulário não contém marca, linha, fabricante nem data de cadastro. Esses campos foram incluídos na API sombra como extensão solicitada anteriormente para rastreabilidade da origem do produto; não são apresentados como paridade com o HTML atual. Não foram criados dados reais ou valores padrão fictícios.

## Listagem e status
- Indicadores classificam como crítico quando quantidade atual <= mínimo.
- Excedente quando máximo > 0 e quantidade atual > máximo.
- Adequado nos demais casos.
- Filtros: adequado, crítico, excedente e todos.
- Tabela exibe foto, etiqueta/código, descrição, quantidade, mínimo/máximo e alerta.
- Dashboard e gráfico também calculam status com quantidade, mínimo e máximo.
- Não foi observada validação de código de barras único, nome único ou limites mínimo/máximo coerentes.

## Foto e leitura de código
- Fotos são compactadas em Gzip e guardadas em Base64 no registro.
- Visualização usa o conteúdo compactado.
- Leitura de código usa câmera e `BarcodeDetector` quando disponível; existe alternativa de digitação manual.
- O scanner depende de suporte do navegador e permissão de câmera.

## Acertos de estoque (`db.acertos_estoque`)
Campos gravados: `id`, `data`, `tipo`, `produtoId`, `quantidade`, `motivo`.
- Tipo: `Entrada` ou `Saída`.
- Produto selecionado por ID de registro do estoque.
- Quantidade deve ser maior que zero na interface.
- Motivo é escolhido pelo nome em `db.motivos_acerto_estoque` e gravado como texto, não ID.
- Entrada soma a quantidade; saída subtrai.
- Se a saída superar o saldo, o original pede confirmação e permite saldo negativo.
- O histórico mostra data/hora, tipo, produto, quantidade e motivo.

## Integridade identificada
- Excluir acerto remove somente o histórico; não reverte a quantidade do produto.
- Excluir produto não impede a exclusão mesmo com acertos associados; o histórico permanece e passa a exibir produto eliminado.
- O original não valida unicidade de etiqueta/código.
- O original não guarda um snapshot do nome do produto no acerto; a listagem tenta resolver o nome pelo `produtoId` atual.

## API sombra criada
- `GET/POST /api/v1/estoque`, `PUT/DELETE /api/v1/estoque/{id}`.
- `GET/POST /api/v1/acertos-estoque`, `DELETE /api/v1/acertos-estoque/{id}`.
- O serviço de acertos atualiza a quantidade do produto e valida existência do produto.
- Diferente do original, a API sombra rejeita saída superior ao saldo com HTTP 409, evitando saldo negativo. Esta é uma regra de segurança adicional explícita, não paridade exata.
- A exclusão do histórico não reverte a quantidade, preservando a semântica observada no original; a futura regra recomendada é estorno compensatório, nunca apagar movimentação sem trilha.
- Na etapa inicial, os serviços eram temporários em memória. A evolução da persistência PostgreSQL e da auditoria transacional está registrada na seção de atualização técnica abaixo; a homologação integrada ainda precisa ser concluída.

## Campos adicionais de rastreabilidade
A API sombra também aceita `marca`, `linha`, `fabricante` e `dataCadastro`, conforme requisito anteriormente solicitado para identificar origem e classificação do produto. Esses campos são extensões novas; a data não é preenchida automaticamente nesta primeira versão.

## Testes
Testes automatizados foram escritos para CRUD, campos adicionais, atualização de saldo, rejeição de saldo insuficiente e produto inexistente. Não foram executados nesta etapa.

## Próximas decisões antes de persistir
1. Definir política de estoque negativo (bloquear ou permitir com autorização).
2. Definir estorno por movimento compensatório, preservando histórico.
3. Proteger exclusão de produto com movimentações.
4. Definir unicidade de etiqueta e normalização de códigos.
5. Definir se marca/linha/fabricante serão texto livre ou cadastros normalizados.
6. Implementar transações no banco para movimentação e saldo atômicos.

## Atualização técnica da branch `bravo-shadow` — 2026-11-28

A persistência PostgreSQL do Estoque e dos Acertos foi ampliada com operações auditadas. Esta atualização descreve implementação em código; não representa liberação para produção ou autorização de importação.

### Operações persistentes auditadas

- Cadastro de produto: INSERT do produto e INSERT de `audit_events` na mesma unidade de trabalho.
- Edição de produto: bloqueio da linha com `SELECT ... FOR UPDATE`, validação do histórico, UPDATE e evento de auditoria na mesma transação.
- Exclusão de produto: DELETE e evento de auditoria na mesma transação; vínculos de movimentação continuam protegidos por FK.
- Acerto de estoque: bloqueio da linha do produto, validação do saldo atualizado, alteração do saldo, INSERT do histórico e evento de auditoria na mesma transação.
- Falha ao inserir auditoria provoca rollback da alteração de negócio.
- Identidade autenticada do Google e request ID são encaminhados pelas rotas aos serviços; serviços persistentes rejeitam mutação sem ator ativo.
- As operações genéricas de escrita dos repositórios permanecem bloqueadas; o caminho dos serviços usa somente os contratos auditados.
- O saldo é validado dentro da transação após o bloqueio da linha, evitando decisões baseadas em leitura concorrente desatualizada.
- O histórico de movimentos continua imutável; correções devem usar movimento compensatório.

### Cobertura automatizada adicionada

- Testes de mesma conexão para saldo, histórico e auditoria.
- Testes de rollback quando a auditoria falha.
- Testes de rollback para criação, edição e exclusão de produto.
- Teste de concorrência real no PostgreSQL descartável: duas saídas concorrentes não podem gerar saldo negativo; apenas a operação vencedora registra histórico e auditoria.
- Teste de integração real que força falha no INSERT de auditoria e verifica que saldo e histórico permanecem inalterados.
- Teste de CRUD auditado do produto no PostgreSQL descartável.

### Estado de homologação

O código e os testes foram adicionados à branch `bravo-shadow`. A homologação depende da conclusão do workflow automatizado com PostgreSQL descartável e da análise de qualquer falha. Até a confirmação do CI, esta etapa permanece **pendente de homologação**. Não houve implantação, conexão com banco de produção, importação de dados reais nem alteração da branch `main`.


## Atualização técnica adicional — categorias e motivos de estoque

Na mesma branch, os catálogos auxiliares de categorias e motivos passaram a gravar criação/exclusão e evento de auditoria na mesma transação PostgreSQL.

- As rotas encaminham o principal Google ativo e o request ID gerado pelo servidor.
- Os serviços persistentes recusam operações sem identidade ativa, request ID ou contrato de auditoria.
- Os repositórios executam INSERT/DELETE e INSERT em `audit_events` na mesma unidade de trabalho.
- Falha na auditoria reverte a alteração do catálogo.
- Exclusão continua protegida por referências de documentos e movimentações; a FK do banco fecha também a condição de corrida entre a checagem e o DELETE.
- Os métodos genéricos de escrita permanecem bloqueados no composition root; somente os métodos auditados são usados pelos serviços.

Foram acrescentados testes de contrato de serviço, mesma conexão, rollback em falha de auditoria e exclusão de registro inexistente. A validação automatizada completa continua pendente; não considerar este módulo homologado até o CI confirmar.


## Atualização técnica adicional — documentos

O módulo Documentos também recebeu contratos de escrita auditada para criação, atualização e exclusão:

- Cada operação de negócio e seu evento de auditoria são executados na mesma unidade de trabalho PostgreSQL.
- Falha ao gravar auditoria reverte a operação documental.
- As rotas passam a encaminhar principal Google ativo e request ID.
- O vínculo opcional com categoria continua protegido por FK; categoria inexistente é conflito e não gera documento.
- O serviço persistente falha de forma fechada se faltar ator, request ID, sink ou método auditado.
- Os testes adicionados cobrem contrato de serviço e rollback de criação, atualização e exclusão em adaptador PostgreSQL controlado.

Esta implementação ainda aguarda o workflow integrado. Não significa homologação, publicação ou autorização de importação.


## Atualização técnica adicional — conselheiros

O cadastro de conselheiros passou a executar criação, atualização e exclusão com auditoria na mesma unidade de trabalho PostgreSQL.

- O serviço exige principal Google ativo, request ID e sink de auditoria.
- Os métodos persistentes auditados executam a alteração e o evento na mesma conexão/transação.
- Atualização e exclusão verificam a existência do registro dentro da própria transação.
- Falha ao inserir auditoria reverte a alteração.
- As rotas encaminham o principal autenticado e o request ID.
- O CRUD genérico continua bloqueado no repositório PostgreSQL composto pela aplicação.

Foram acrescentados testes para as três operações, rollback por falha de auditoria e contrato do serviço. O CI integrado permanece pendente; o módulo não está homologado. O cadastro de dados do condomínio ainda permanece bloqueado até implementação de atualização auditada e preservação transacional de patches.
