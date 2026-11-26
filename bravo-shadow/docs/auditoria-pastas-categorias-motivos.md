# Auditoria de Pastas & Categorias e Motivos de Acerto de Estoque

## Fonte
Inspeção estática do `index.html` na branch `upgrade/project-hardening`, SHA `873dbf37bbcf2082faa0444ac28cb9ca9f8ff21c`. O arquivo original permaneceu intacto.

## Pastas Gerais (`db.categorias`)
- Estrutura persistida observada: `id`, `nome`.
- Cadastro gera `cat_` + timestamp.
- Nome é obrigatório no formulário.
- A tela permite cadastrar e excluir; não há edição ou ordenação observada.
- Não foi identificada validação de unicidade nem proteção contra exclusão de pastas utilizadas.
- A lista é consumida pelo formulário de documentos como opções de `pasta`.
- O documento grava `pasta` como texto (nome), não como ID. Se não houver pastas cadastradas, o formulário apresenta opções de fallback: Geral, Assembleias, Financeiro e Manutenção.
- A exclusão de uma pasta não atualiza os documentos que já guardam aquele nome. Portanto, podem permanecer documentos apontando para um nome de pasta que já não consta no cadastro.

## Motivos de Acerto (`db.motivos_acerto_estoque`)
- Estrutura persistida observada: `id`, `nome`.
- Cadastro gera `mot_` + timestamp.
- Nome é obrigatório no formulário.
- A tela permite cadastrar e excluir; não há edição, ordenação, unicidade ou verificação de uso observada.
- O modelo padrão contém os nomes Perca / Avaria, Quebra, Ajuste de Inventário e Doação / Uso Interno. Esses são valores de inicialização do original e não foram copiados como dados reais para a sombra.
- A auditoria de texto do HTML não encontrou campo `motivoId` ou `motivoAcerto` em `acertos_estoque`. Não foi possível afirmar vínculo persistido entre um acerto e um motivo; não foi criado vínculo na API sombra.

## APIs criadas na sombra
- Pastas: `GET/POST /api/v1/categorias`, `DELETE /api/v1/categorias/{id}`.
- Motivos: `GET/POST /api/v1/motivos-acerto-estoque`, `DELETE /api/v1/motivos-acerto-estoque/{id}`.
- Ambos mantêm somente `id` e `nome`; nomes obrigatórios. Não foram acrescentadas regras de unicidade ou edição que não existiam no original.
- Serviços usam memória temporária; não há conexão com Supabase nem frontend integrado.

## Integridade e próximos cuidados
A relação textual entre `documentos.pasta` e `categorias.nome` merece evolução planejada para um identificador estável, com migração e compatibilidade para documentos antigos. Isso não deve ser feito sem uma estratégia explícita para preservar os documentos existentes. A exclusão continua com paridade funcional simples nesta etapa; antes de persistência real, recomenda-se proteção de exclusão ou política de arquivamento para pastas em uso.

## Limites
Auditoria estática; sem dados reais, execução no navegador ou execução dos testes automatizados.
