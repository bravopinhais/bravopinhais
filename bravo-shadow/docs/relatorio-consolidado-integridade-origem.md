# Relatório consolidado de integridade da origem

**Branch:** `bravo-shadow`  
**Status:** camada de avaliação somente leitura; não é importador e não autoriza carga.

## Objetivo

Reunir em uma única resposta estrutural os quatro avaliadores existentes:

1. Inventário agregado de coleções e campos.
2. Compatibilidade dos campos com os contratos de destino Shadow.
3. Contratos especiais de Financeiro, Documentos, Estoque e Acertos de Estoque.
4. Reconciliação das referências confirmadas entre Financeiro/Plano de Contas e Acertos de Estoque/Produtos.

A função `build_source_integrity_report` recebe um objeto `collections` já decodificado e devolve o relatório consolidado. Não lê arquivo, não chama rede, não acessa banco e não persiste resultado.

## Conteúdo do relatório

### Resumo agregado

- total de coleções e registros;
- registros inválidos, sem ID e com IDs duplicados;
- coleções com problemas de estrutura;
- avaliações de compatibilidade que exigem revisão;
- contratos especiais que exigem revisão;
- referências órfãs e regras de referência não resolvidas;
- coleções de referência ausentes e containers inválidos;
- domínios especiais ainda não avaliados automaticamente;
- status geral e códigos de ocorrência.

### Detalhes técnicos

O relatório também agrega os resultados originais dos avaliadores de inventário, compatibilidade, contratos especiais e referências. Os resultados são somente estruturais: não incluem valores de registros, IDs, CPF, telefone, e-mail, endereço, Base64 ou conteúdo de documentos.

## Regra do status geral

- `structurally_clear`: nenhum código de ocorrência foi identificado pelos avaliadores executados.
- `review_required`: existe ao menos um código de ocorrência ou domínio ainda não avaliado.

Mesmo `structurally_clear` não equivale a autorização para importar. Aprovação transacional, regras de negócio, destino local descartável, manifesto aprovado e autorização do operador permanecem gates independentes.

Na implementação atual, o relatório tende corretamente a `review_required` enquanto os contratos especiais conservarem bloqueios de domínio e o singleton de Condomínio não tiver localizador confirmado.

## Mapeamentos

Os mapeamentos de compatibilidade comum e contratos especiais são argumentos separados e explícitos. Não se presume que um nome alternativo seja correto. Referências entre coleções usam somente as regras confirmadas no contrato legado; a camada consolidada não inventa novos relacionamentos.

## Limites e segurança

- Nenhuma transformação, correção, associação, descarte ou geração de payload.
- Nenhum acesso a dados reais ou ao banco.
- Nenhum log de conteúdo ou valor pessoal.
- Coleção ausente não é confundida com coleção vazia.
- O relatório não substitui a verificação de hash do snapshot/envelope.
- O singleton de Condomínio continua pendente de localização manual.
- Documentos e fotos ainda exigem identificação do codec e validação controlada.
- Financeiro e Estoque ainda exigem decisões de precisão e reconciliação de domínio.

## Próxima etapa

Preparar um manifesto de pré-importação que vincule o hash do snapshot, versões de contratos/mapeamentos e resultado do relatório consolidado. O manifesto deverá ser reproduzível e aprovado antes de qualquer escrita no banco local descartável.
