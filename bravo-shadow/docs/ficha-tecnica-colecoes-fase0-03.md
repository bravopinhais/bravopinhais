# Ficha técnica — coleções da Fase 0 (lote 03)

**Escopo:** Moradores, Fornecedores e Empregados.  
**Fonte legada:** `index.html`, branch `bravo-shadow` (arquivo original, somente leitura).  
**Objetivo:** registrar equivalência de campos e operações antes de qualquer extração ou carga.  
**Status:** levantamento estático; nenhuma migração de dados executada.

## 1. Moradores

**Coleção legada:** `db.moradores[]`

| Campo legado | Tipo/uso observado | Shadow |
|---|---|---|
| `id` | identificador textual; gerado como `mor_<timestamp>` no cadastro e `mor_imp_<timestamp>_<linha>` no CSV | `id: str` |
| `bloco` | texto; padrão visual/importação `1` | `bloco: str` |
| `apartamento` | texto | `apartamento: str` |
| `nome` | texto | `nome: str` |
| `email` | texto opcional, vazio permitido | `email: str = ""` |
| `telefone` | texto opcional; preservar máscara/pontuação | `telefone: str = ""` |
| `cpf` | texto opcional; preservar máscara/pontuação | `cpf: str = ""` |
| `petNome` | texto opcional | `petNome: str = ""` |
| `vagaGaragem` | texto opcional | `vagaGaragem: str = ""` |

**Operações legadas observadas:** listagem; filtro por bloco; busca por nome/apartamento; cadastro/edição; exclusão; importação CSV. A importação CSV tenta reconhecer cabeçalhos de bloco, apartamento/unidade, nome/morador/proprietário, e-mail, telefone, CPF/documento/RG, pet/animal e vaga/garagem. Sem cabeçalho reconhecido, usa posições iniciais para bloco, apartamento e nome. O parser divide por vírgula ou ponto e vírgula e remove aspas externas; não é um parser CSV robusto para campos com delimitadores internos.

**Shadow:** schema contém os nove campos de negócio; strings são aparadas sem remover pontuação de CPF/telefone. Há endpoints GET (filtros `bloco` e `busca`), POST, PUT, DELETE e POST `/importar`. O DTO de importação aplica defaults `bloco="1"` e `nome="Sem Nome"`.

**Diferenças/gates:**
- O serviço Shadow gera novos IDs `mor_shadow_<uuid>` no cadastro e `mor_import_<uuid>` na importação. O DTO de importação não aceita `id`. Portanto, **a importação atual não preserva IDs legados**; criar um caminho de migração que aceite ID legado validado, sem alterar o comportamento normal de cadastro.
- Confirmar se o filtro de bloco deve considerar string vazia e se a busca precisa incluir e-mail, CPF ou telefone; hoje a equivalência observada é nome/apartamento.
- CSV legado não deve ser usado como formato de migração canônica; preferir extração estruturada do payload JSON para evitar perda por parsing.

## 2. Fornecedores

**Coleção legada:** `db.fornecedores[]`

| Campo legado | Tipo/uso observado | Shadow |
|---|---|---|
| `id` | identificador textual; gerado como `for_<timestamp>` | `id: str` |
| `cnpj` | texto, exibido como texto monoespaçado | `cnpj: str` |
| `razaoSocial` | texto | `razaoSocial: str` |

**Operações legadas observadas:** listagem; cadastro/edição; exclusão. O formulário e a rotina de gravação observados trabalham com CNPJ e razão social.

**Shadow:** schema mantém CNPJ e razão social como strings obrigatórias e aparadas; endpoints GET, POST, PUT e DELETE.

**Diferenças/gates:**
- Serviço Shadow gera `for_shadow_<uuid>` no cadastro; o schema de entrada não recebe ID. A importação de legado precisa preservar o ID original por um mecanismo específico.
- Não foi identificada validação de dígitos verificadores, normalização de pontuação ou unicidade de CNPJ no schema consultado. Não introduzir essas regras durante a migração sem decisão e saneamento prévios.
- Verificar referências a fornecedores em outras coleções/rotinas antes de permitir exclusões ou definir integridade referencial.

## 3. Empregados

**Coleção legada:** `db.empregados[]`

| Campo legado | Tipo/uso observado | Shadow |
|---|---|---|
| `id` | identificador textual; gerado como `emp_<timestamp>` | `id: str` |
| `nome` | texto obrigatório no formulário | `nome: str` |
| `cargo` | texto obrigatório no formulário | `cargo: str` |
| `empresa` | texto opcional | `empresa: str = ""` |
| `endereco` | texto opcional | `endereco: str = ""` |
| `telefone` | texto opcional | `telefone: str = ""` |
| `contatoEmergenciaNome` | texto opcional | `contatoEmergenciaNome: str = ""` |
| `contatoEmergenciaTel` | texto opcional | `contatoEmergenciaTel: str = ""` |

**Operações legadas observadas:** listagem; cadastro/edição; exclusão. A listagem apresenta nome/função, empresa, endereço, telefone e contato de emergência.

**Shadow:** schema contém os sete campos de negócio; todas as strings são aparadas. Endpoints GET, POST, PUT e DELETE.

**Diferenças/gates:**
- Serviço Shadow gera `emp_shadow_<uuid>` no cadastro; o schema de entrada não recebe ID. A carga migratória deverá preservar IDs legados por caminho específico.
- Não foram observados campos de matrícula, CPF, datas de admissão/desligamento, salário ou situação funcional no formulário/objeto consultado. Não presumir que esses dados existam na coleção atual.
- Verificar referências a empregados em outras coleções antes de definir exclusão e integridade referencial.

## 4. Regras de migração comuns

1. Extrair diretamente as três coleções do objeto JSON legado, preservando cada `id` original como string e todos os campos existentes.
2. Não substituir IDs por UUIDs Shadow nem gerar novos IDs durante carga de legado.
3. Preservar pontuação e zeros à esquerda em documentos e telefones; não converter CNPJ/CPF/telefone para número.
4. Registrar contagem de origem, contagem importada, IDs duplicados, campos inesperados e rejeições; interromper lote se houver perda ou colisão.
5. Não inferir campos ausentes, não usar dados de demonstração/`DEFAULT_DATA` e não conectar ao banco de produção.
6. Antes de implementar a carga, definir estratégia de idempotência (reexecutar sem duplicar), relatório de divergências e rollback do lote.

## 5. Evidências e limites

- O código legado foi consultado por inspeção estática de `index.html`; seu SHA permaneceu `873dbf37bbcf2082faa0444ac28cb9ca9f8ff21c`.
- Schemas, routers e services Shadow foram lidos na branch `bravo-shadow`.
- Este documento não comprova execução de testes, validação em navegador, extração de dados ou integração com PostgreSQL.
