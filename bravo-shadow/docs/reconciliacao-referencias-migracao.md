# Reconciliação de referências da migração

**Branch:** `bravo-shadow`  
**Status:** avaliador estrutural somente leitura; não é importador nem transformador.

## Relações confirmadas na origem auditada

| Origem | Campo | Destino | Chave | Regra |
|---|---|---|---|---|
| Financeiro | `planoContaId` | Plano de Contas | `id` | Opcional; valor vazio é contado separadamente |
| Acertos de Estoque | `produtoId` | Estoque | `id` | Obrigatório; vazio ou ausente exige revisão |

Nenhuma outra relação é ativada por padrão. Categorias de documentos e motivos de acerto permanecem fora da reconciliação automática enquanto não houver campo de referência de origem comprovado.

## O que o avaliador verifica

- Correspondência de IDs textuais exatos, sem conversão numérica ou normalização.
- Referências órfãs.
- Referências opcionais vazias e referências obrigatórias vazias/inválidas.
- Campo de referência ausente.
- IDs de destino duplicados ou ausentes.
- Coleção ausente, coleção presente e vazia, e container de coleção inválido.
- Registros de origem que não sejam objetos.

A saída contém somente nomes de coleções/campos e contagens agregadas. Não contém IDs, valores de referência, payloads, dados pessoais ou conteúdo de documentos.

## Classificações

- `references_resolved`: todas as verificações estruturais das relações confirmadas foram satisfeitas.
- `review_required`: existe ausência, vazio estrutural, duplicidade, órfão, tipo inválido ou coleção não verificável.

Mesmo `references_resolved` não aprova importação. Regras de domínio, tipos, valores, permissões, transações e demais bloqueios dos contratos especiais continuam aplicáveis.

## Limites

- O avaliador não corrige, cria, exclui ou associa registros.
- Não tenta descobrir aliases de coleções ou campos.
- Não faz correspondência por nome, aproximação textual ou CNPJ/CPF.
- Não resolve relações polimórficas ou relações não confirmadas.
- Não valida a semântica de datas, decimais, documentos ou saldos.
- Não conecta a banco, não grava relatórios e não lê arquivos diretamente.
- Coleções ausentes não são tratadas como vazias; ambas bloqueiam a aceitação, mas são diferenciadas no relatório.

## Próximo bloqueio

Antes de qualquer piloto, ainda é necessário confrontar os contratos com um snapshot sintético/anônimo representativo, confirmar o localizador do singleton de Condomínio e concluir o modelo transacional e as permissões do banco local descartável.
