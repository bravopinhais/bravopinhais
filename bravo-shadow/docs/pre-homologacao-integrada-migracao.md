# Pré-homologação integrada da migração

## Fluxo único

`run_integrated_migration_preflight(collections)` combina, em memória e somente leitura:

1. Inventário estrutural agregado (tipos, presença, IDs ausentes/duplicados).
2. Compatibilidade dos campos com os contratos Shadow e mapeamentos explícitos.
3. Contratos especializados de Financeiro, Documentos, Estoque e Acertos.
4. Reconciliação das duas referências legadas confirmadas por ID exato.
5. Avaliação de valores e documentos por registro, com contagem de ocorrências.

## Resultado

O relatório agrupa os resultados por subsistema e apresenta códigos de bloqueio. Não contém valores de registros, IDs de origem ou conteúdo de documentos. Não altera o snapshot nem constrói comandos/payloads de importação.

## Política de liberação

- `blocked`: entrada não é um objeto de coleções.
- `review_required`: há qualquer pendência estrutural, mapeamento, referência, valor ou aprovação de domínio.
- `assessment_clear_not_import_authorized`: apenas quando todos os verificadores estiverem limpos; não concede autorização de importação.

Os contratos especializados mantêm aprovação de domínio pendente intencionalmente até regras de conversão, exceções e mapeamentos serem aprovados. Condomínio permanece com localizador singleton manual. Compatibilidade incompleta não é presumida como resolvida.

## Segurança e limites

- Não acessa arquivos, rede, banco ou APIs.
- Não executa SQL nem grava dados.
- Não transforma valores, aplica defaults, arredonda ou corrige saldos.
- Não importa nem autoriza importação.
- Caller deve fornecer snapshot sintético nesta fase.

Testes sintéticos foram escritos e não executados.
