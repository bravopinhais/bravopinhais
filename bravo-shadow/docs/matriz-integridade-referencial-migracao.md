# Matriz de integridade referencial da migração

**Estado:** revisão estática e conservadora. Não é autorização para importar.

## Vínculos legados confirmados

| Origem | Campo legado | Destino | Regra |
|---|---|---|---|
| `financeiro` | `planoContaId` | `plano_contas.id` | Opcional; correspondência exata |
| `acertos_estoque` | `produtoId` | `estoque.id` | Obrigatório; correspondência exata |

Essas são as únicas regras confirmadas no reconciliador atual. Referências órfãs, valores inválidos, campos ausentes e IDs de destino duplicados bloqueiam a liberação estrutural.

## FKs existentes no DDL Shadow

O rascunho `sql-piloto-financeiro.sql` também declara:

- `documentos.categoria_id → categorias.id`
- `acertos_estoque.motivo_id → motivos_acerto.id`

Esses campos de destino não possuem, no contrato legado auditado, um campo de origem comprovado equivalente. Portanto:

- Não copiar `categoria_id` ou `motivo_id` por suposição.
- Não converter texto de categoria/motivo em ID automaticamente.
- Manter o vínculo nulo quando o DDL permitir e a regra de negócio aprovar.
- Se for necessário reconstruir o vínculo, exigir tabela de correspondência explícita, única, revisada e registrada no manifesto.
- A ausência de vínculo opcional não significa que o relacionamento foi reconciliado.

## Limites da validação atual

1. O reconciliador compara IDs textuais exatos; não normaliza, converte ou remove zeros à esquerda.
2. A presença de uma FK no DDL não prova que o snapshot legado contenha a referência.
3. A regra de estoque exige produto existente, mas não resolve divergência entre saldo cadastrado e histórico de movimentos.
4. A regra financeira não autoriza conversão de valores numéricos para centavos/decimal; precisão permanece sujeita ao contrato especial financeiro.
5. O objeto singleton de Condomínio continua fora da reconciliação de coleções e exige localizador manual e cardinalidade exatamente um.
6. Outras referências só entram na matriz depois de confirmação do campo de origem e do significado funcional.

## Verificação sintética adicionada

O teste estático confere que as duas regras legadas explícitas correspondem às FKs do DDL e que os dois vínculos adicionais do destino não sejam apresentados como referências legadas confirmadas. O teste foi escrito, mas não executado.

## Bloqueio para homologação

Ainda é necessário validar os tipos SQL reais, constraints, cardinalidades e dados sintéticos em PostgreSQL descartável. Nenhum DDL foi aplicado e nenhuma conexão foi aberta.
