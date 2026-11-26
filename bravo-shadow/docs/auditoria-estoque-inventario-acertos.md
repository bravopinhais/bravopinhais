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
- Os serviços são temporários em memória. Não há persistência, concorrência transacional entre instâncias, frontend integrado ou conexão de produção.

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