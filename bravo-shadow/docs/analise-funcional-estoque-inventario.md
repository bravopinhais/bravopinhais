# Análise funcional — Estoque & Inventário

Data da inspeção: 27/11/2026
Escopo: comparação estática do módulo legado com a branch bravo-shadow.

## 1. Legado observado

O painel calcula totais de itens adequados, críticos e excedentes. Considera crítico o saldo menor ou igual ao mínimo; excedente quando o máximo é positivo e o saldo ultrapassa esse limite; os demais ficam adequados. Há filtros por situação, gráfico de status e tabela com foto, etiqueta/código, descrição, quantidade, mínimo/máximo, alerta e ações de edição/exclusão.

O formulário básico observado no legado contém etiqueta/código de barras, descrição do item, quantidade atual, mínimo, máximo e foto compactada em Gzip. Há fluxo de scanner por câmera com leitura por BarcodeDetector quando disponível e alternativa de digitação manual. A foto é compactada no navegador para Gzip/Base64.

## 2. Contrato Shadow

### Schema

EstoqueInput contém: item; quantidade; minimo; maximo; etiqueta; fotoNome; fotoCompactadaGzip; marca; linha; fabricante; dataCadastro; setor; unidade; valorUnitario; status; cor; fotoPath.

Quantidades e limites: Decimal não negativo, até 14 dígitos e 3 casas decimais. Valor unitário: Decimal não negativo, até 14 dígitos e 2 casas. Data de cadastro opcional em AAAA-MM-DD e validada como data real. Campos textuais são aparados e campos extras recusados.

### API

- GET /api/v1/estoque — estoque:read.
- POST /api/v1/estoque — estoque:create.
- PUT /api/v1/estoque/{item_id} — estoque:update.
- DELETE /api/v1/estoque/{item_id} — estoque:delete.

Admin e Operador têm CRUD de produtos no catálogo de capacidades atual.

### Persistência e integridade

O adapter PostgreSQL persiste os campos do schema em bravo_shadow.estoque. Edição cadastral usa transação e bloqueio da linha do produto. Se existem acertos vinculados, a quantidade não pode ser alterada pelo cadastro. O service também bloqueia exclusão quando existem referências de movimentação. Ajustes de saldo devem ocorrer no módulo Acerto de Estoque.

## 3. Interface adicionada nesta etapa

A função estoqueView() foi adicionada ao frontend Shadow e ligada à navegação do módulo estoque. A interface inclui campos de cadastro para todos os campos do contrato, filtros estruturais, indicadores e tabela com identificação, origem, setor, saldo e limites.

Os campos marca, linha, fabricante e data de cadastro foram explicitamente incluídos para rastreabilidade de origem do produto. Quantidade usa três casas decimais; valor unitário, duas.

Todos os controles estão desabilitados. Não há chamadas de rede nem produtos fictícios. A tela não afirma que scanner, upload, preview de fotos ou relatórios estejam funcionais.

## 4. Lacunas e riscos

1. A interface ainda não integra a API nem autenticação Google/Bearer.
2. A API de listagem retorna a coleção sem filtros/paginação; os filtros visuais não executam consultas.
3. Scanner por câmera e digitação assistida de código não foram ligados à tela Shadow.
4. Foto Gzip/Base64 e fotoPath existem no contrato, mas armazenamento externo, limites de tamanho, preview, URLs assinadas, órfãos e otimização não estão implementados nesta tela.
5. Impressão de etiquetas/códigos, checklist de inspeção/entrega/devolução e relatórios por setor não estão integrados.
6. O histórico é mantido no módulo de acertos; operações de saldo não devem ser feitas por edição cadastral após a primeira movimentação.
7. Auditoria completa de CRUD de produto não foi confirmada nesta inspeção.
8. A API não expõe versionamento If-Match/ETag para edição do produto, embora o adapter tenha versionamento interno.

## 5. Critérios para habilitação futura

- Integrar sessão Google validada e token Bearer a uma API HTTPS isolada.
- Implementar filtros/paginação de consulta e conferir permissões por perfil.
- Definir armazenamento seguro de imagens, limites, preview e política de retenção.
- Integrar scanner, etiquetas, checklist e relatórios por setor antes de anunciar esses recursos como disponíveis.
- Garantir que todo ajuste de saldo use o fluxo transacional de Acerto de Estoque.
- Adicionar controle de concorrência HTTP e auditoria de operações.

## 6. Limites desta entrega

Esta etapa é interface visual e documentação. Não executou testes, não aplicou SQL, não conectou banco, não publicou frontend/API e não alterou main ou dados de produção.