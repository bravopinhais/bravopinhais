# Auditoria de Moradores & Unidades

## Fonte
Inspeção estática do `index.html` na branch `upgrade/project-hardening`, SHA `873dbf37bbcf2082faa0444ac28cb9ca9f8ff21c`. O original não foi alterado.

## Estrutura observada em `db.moradores`
- `id`: novo cadastro manual usa prefixo `mor_` + timestamp; importação usa `mor_imp_` + timestamp + índice da linha.
- `bloco`: obrigatório no formulário; default visual "1".
- `apartamento`: obrigatório no formulário.
- `nome`: obrigatório no formulário.
- `email`: opcional, campo HTML type=email.
- `telefone`: opcional.
- `cpf`: opcional; rótulo apresentado como "CPF / RG".
- `petNome`: opcional; rótulo "Pet (Espécie / Nome)".
- `vagaGaragem`: opcional; rótulo "Vaga / Estacionamento".

A edição reconstrói o objeto com esses campos. Propriedades adicionais são descartadas na gravação do formulário.

## Listagem e filtros
- Listagem exibe bloco/apartamento, nome, e-mail, CPF/RG, telefone, pet e vaga/estacionamento.
- Filtro de bloco por igualdade textual, após trim.
- Pesquisa por trecho do nome ou apartamento, sem distinção entre maiúsculas/minúsculas.
- Não foi observada ordenação ou validação de unicidade de unidade, CPF ou e-mail.

## Importação atual
A interface aceita arquivo de planilha/CSV, identifica colunas pelo cabeçalho e reconhece sinônimos:
- bloco/bl;
- apartamento/unidade/ap/casa;
- nome/morador/proprietário;
- e-mail;
- telefone/celular/WhatsApp/fone;
- CPF/documento/RG;
- pet/animal;
- vaga/estacionamento/garagem.

Quando não encontra cabeçalho correspondente, usa fallback posicional para bloco, apartamento e nome. Defaults observados: bloco "1", apartamento vazio, nome "Sem Nome"; demais campos vazios. Linhas vazias são ignoradas.

Limitação técnica observada: cada linha é dividida por vírgula ou ponto e vírgula com expressão simples, removendo aspas nas extremidades. Isso não implementa corretamente CSV com delimitadores dentro de campos entre aspas, nem parsing real de XLSX. A extensão do arquivo e o conteúdo devem ser verificados antes de evoluir a importação. A rotina não verifica duplicidade e simplesmente acrescenta registros.

## CRUD inicial da sombra
- `GET/POST /api/v1/moradores`
- `GET /api/v1/moradores?bloco=...&busca=...`
- `PUT/DELETE /api/v1/moradores/{id}`
- `POST /api/v1/moradores/importar` para lote de registros já estruturados (JSON), não para upload direto de XLSX/CSV.

O endpoint de lote não tenta adivinhar cabeçalhos nem detectar duplicidades, para evitar regras não aprovadas. IDs são gerados na sombra. Dados são mantidos somente em memória.

## Privacidade e integridade
CPF/RG, e-mail, telefone e dados de unidade são informações pessoais. Não foram copiados dados reais para a sombra. Antes de persistir ou disponibilizar o módulo, serão necessários autorização por perfil, trilha de auditoria e proteção adequada. Não foi presumido vínculo automático com Financeiro, Conselho ou Usuários.

## Limitações da auditoria
Análise estática do código, sem execução do formulário no navegador, sem leitura de dados reais do Supabase e sem execução dos testes automatizados.
