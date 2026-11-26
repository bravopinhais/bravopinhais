# Evidências de relacionamentos no código legado — Fase 0

**Origem inspecionada:** `index.html`, branch `upgrade/project-hardening`, blob SHA `873dbf37bbcf2082faa0444ac28cb9ca9f8ff21c`.  
**Método:** inspeção estática de renderizadores, formulários e funções de gravação. Nenhum dado persistido, credencial ou banco foi consultado.  
**Objetivo:** validar quais vínculos são realmente usados pelo código legado e quais eram apenas hipóteses estruturais.

## 1. Relações comprovadas no código

| Coleção de origem | Coleção de destino | Evidência no legado | Conclusão técnica |
|---|---|---|---|
| `financeiro` | `plano_contas` | Linha 1517 inicializa `planoContaId`; linhas 1536 e 1554 carregam e gravam o ID selecionado; linha 1496 resolve a conta pelo ID. | FK lógica explícita, opcional (a opção vazia é permitida). Não presumir que todo título tenha conta. |
| `acertos_estoque` | `estoque` | Linha 2383 resolve o produto por `ac.produtoId`; linhas 2477–2483 validam e localizam o produto; linha 2501 grava `produtoId`. | FK lógica explícita para o produto. Movimento deve manter o ID legado e ser importado após o cadastro de estoque. |
| `documentos` | `categorias` | Linha 2573 deriva as opções de pasta de `db.categorias.map(c => c.nome)`; linhas 2585 e 2621 gravam o nome escolhido em `pasta`. | Dependência por texto/nome, não por ID. A categoria pode ser excluída ou renomeada sem FK formal visível; não criar FK automática em caso ambíguo. |

## 2. Estruturas que não são relações formais

### Conselho e Condomínio
- Linhas 1328–1355 carregam `db.condominio` e `db.conselheiros` separadamente na mesma tela.
- Linhas 1380 e 1399–1408 editam e gravam conselheiros com `id`, `nome`, `cargo`, `BlocoAp` e `telefone`.
- A função `salvarDadosCondominio` (linhas 1363–1378) atualiza os campos do objeto `db.condominio`; não atribui `condominioId` aos conselheiros.
- **Conclusão:** há associação de apresentação/contexto, mas não foi encontrada FK explícita entre conselheiros e condomínio. Não criar FK nem cardinalidade por suposição.

### Moradores, blocos e apartamentos
- A importação CSV constrói campos `bloco` e `apartamento` como valores textuais (linhas 563–583).
- O formulário do morador grava ambos como texto no próprio registro (linhas 1751–1790).
- Os filtros e a listagem usam esses campos diretamente (linhas 1641–1653 e 1708).
- **Conclusão:** não foi encontrada coleção independente de unidades nem `unidadeId`/FK. Preservar bloco e apartamento como texto, inclusive zeros à esquerda. Não normalizar em cadastro de unidades nesta migração.

### Motivos de Acerto e Acertos de Estoque
- A tela de motivos mantém `db.motivos_acerto_estoque` separadamente (linhas 1931, 2008–2015).
- O formulário de movimento apresenta os nomes dos motivos como opções (linha 2440, no bloco de cadastro do acerto) e grava o valor textual em `motivo` (linha 2502).
- **Conclusão:** o legado não grava `motivoId` no movimento. Preservar o texto; só associar ao ID Shadow quando houver correspondência exata e única.

### Forma Monetária e Contas Bancárias
- A inspeção dos formulários e gravações identificados não encontrou `formaMonetariaId`, `contaBancariaId` ou outro campo de vínculo no objeto Financeiro.
- **Conclusão:** não há evidência para ligar títulos financeiros a formas monetárias ou contas bancárias. Manter cadastros separados até nova evidência.

## 3. Dependências derivadas, não relações de propriedade

- Dashboard (linhas 1084 em diante) lê e agrega moradores, fornecedores, documentos, estoque e financeiro. Isso representa dependência de consulta, não FK entre essas coleções.
- DRE/Relatórios (linhas 2760–2778) agrega títulos Financeiros e Plano de Contas; o agrupamento usa `planoContaId`. Títulos sem plano entram nos totais gerais e não nas linhas agrupadas por conta.
- Não importar métricas do Dashboard/DRE como registros-base.

## 4. Consequências para o desenho do importador

1. Preservar IDs de `financeiro.planoContaId` e `acertos_estoque.produtoId`; validar referências antes de inserir.
2. Preservar `documentos.pasta` e `acertos_estoque.motivo` como texto original. A conversão para FK no Shadow é uma transformação opcional e auditável, nunca substituição do texto legado.
3. Manter `conselheiros` e `condominio` como coleções/objetos independentes enquanto não houver campo de vínculo comprovado.
4. Manter `moradores.bloco` e `moradores.apartamento` como texto; não criar tabela de unidades por inferência.
5. Não associar Financeiro a Forma Monetária ou Conta Bancária sem campo e regra comprovados.
6. Tratar Dashboard/DRE como consumidores derivados, reconstruídos após importação e reconciliação das fontes.

## 5. Pendências que exigem evidência adicional

- Confirmar o formato real do payload persistido e se há dados históricos com campos adicionais que não aparecem nos formulários atuais.
- Verificar exclusões/renomeações de categorias e motivos e o efeito nos registros já existentes.
- Confirmar se a instalação ativa possui extensão customizada que introduza relações não presentes neste baseline.
- Aprovar política de órfãos, duplicidades e vínculos ambíguos antes de qualquer carga.

**Status:** evidências de código consolidadas; não é autorização para executar importação, conectar produção ou aplicar migrations.
