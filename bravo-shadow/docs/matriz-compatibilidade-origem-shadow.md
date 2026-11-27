# Matriz de compatibilidade — origem legada x Bravo Shadow

**Status:** avaliação estrutural estática; não transforma nem importa registros.  
**Branch:** `bravo-shadow`.  
**Base:** schemas Pydantic atuais dos módulos Shadow.  
**Dados:** somente contratos e fixtures sintéticas.

## Objetivo

Comparar o inventário de campos de uma coleção de origem com o contrato de destino do Shadow e produzir um relatório agregado. A avaliação usa nomes exatos de campos. Não tenta adivinhar aliases, não aplica defaults, não converte valores e não cria payloads de importação.

## Coleções com contrato de destino descrito

| Destino Shadow | Campos obrigatórios | Campos opcionais |
|---|---|---|
| Categorias | `id`, `nome` | — |
| Motivos de Acerto | `id`, `nome` | — |
| Fornecedores | `id`, `cnpj`, `razaoSocial` | — |
| Empregados | `id`, `nome`, `cargo` | `empresa`, `endereco`, `telefone`, `contatoEmergenciaNome`, `contatoEmergenciaTel` |
| Moradores | `id`, `bloco`, `apartamento`, `nome` | `email`, `telefone`, `cpf`, `petNome`, `vagaGaragem` |
| Conselheiros | `id`, `nome`, `cargo` | `BlocoAp`, `telefone` |
| Plano de Contas | `id`, `codigo`, `nome`, `tipo` | — |
| Formas Monetárias | `id`, `nome` | `multaPct` |
| Contas Bancárias | `id`, `banco` | `saldo` |

O campo `version` de Plano de Contas é metadado controlado pelo Shadow e não faz parte da carga legada.

## Classificações

- `compatible`: campos esperados encontrados, sem divergência de tipo observada.
- `compatible_with_optional_gaps`: faltam somente campos opcionais; o Shadow poderá aplicar seu contrato padrão apenas após aprovação explícita da regra de importação.
- `review_required`: campo obrigatório ausente, tipo incompatível/conversão pendente ou campo de origem sem destino mapeado.
- Coleção de origem sem mapeamento e destino sem coleção de origem aparecem separadamente no relatório.

Campos extras são bloqueadores de revisão, não são descartados. Para `saldo` decimal, texto decimal é aceito para avaliação preliminar; número JSON exige revisão porque não comprova preservação de precisão. Para `multaPct`, o destino é numérico e a avaliação exige número JSON.

## Limites conhecidos

1. Os nomes exatos das coleções no arquivo legado ainda precisam ser confirmados. O mapeamento padrão usa nomes idênticos apenas como convenção inicial; nomes diferentes exigem `source_to_target` explícito.
2. A matriz reflete os schemas atuais, não confirma que o legado contém todos esses campos ou que os nomes coincidem.
3. Condomínio ainda exige contrato de destino dedicado e revisão de todos os campos institucionais.
4. Financeiro, Documentos e Acertos de Estoque permanecem fora deste primeiro mapeamento simples por exigirem regras próprias de precisão, referências, conteúdo binário e/ou transação.
5. Campos extras precisam de decisão: preservar em extensão/histórico, mapear para campo aprovado ou bloquear a coleção. Nunca ignorar silenciosamente.
6. O relatório usa apenas nomes de campos, contagens e tipos agregados; não expõe IDs nem valores pessoais.

## Implementação

- `backend/app/core/migration_compatibility.py`: contratos declarativos e avaliador puro.
- `backend/app/core/migration_source_inventory.py`: inventário agregado e privado.
- `backend/app/core/migration_envelope_reader.py`: inclui o inventário na leitura validada do envelope.
- `backend/tests/test_migration_compatibility.py`: casos sintéticos para correspondência exata, campos obrigatórios ausentes, decimal numérico, campos extras e alias explícito.

**Não realizado:** leitura de arquivo real, conexão com banco, migração SQL, execução de testes, importação ou deploy.
