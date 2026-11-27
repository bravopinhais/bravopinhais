# Análise funcional — Moradores & Unidades

Data: 2026-11-27  
Escopo: inspeção estática do legado, schema, service, router, autorização e adapter PostgreSQL Shadow.

## Fluxo legado identificado

### Listagem e filtros

A tela `renderMoradoresView` apresenta os moradores em tabela, com:
- Bloco e apartamento;
- Nome e e-mail;
- CPF/RG;
- Telefone;
- Pet;
- Vaga de garagem;
- Ações de editar e excluir.

Os filtros legados permitem selecionar um bloco disponível e pesquisar por nome ou apartamento. Há ação para limpar filtros. A lista é filtrada no navegador.

### Cadastro e edição

O modal contém os campos:
- Bloco (obrigatório; novo registro inicia em “1”);
- Apartamento (obrigatório);
- Nome completo (obrigatório);
- E-mail;
- Telefone/WhatsApp;
- CPF/RG;
- Pet (espécie/nome);
- Vaga/estacionamento.

O legado salva a coleção e atualiza a listagem. Não foi identificada no fluxo inspecionado validação de unidade única ou vínculo com uma entidade de unidade separada.

### Importação CSV/TXT

O legado aceita arquivo CSV/TXT, identifica cabeçalhos aproximados para bloco, apartamento/unidade/casa, nome/morador/proprietário, e-mail, telefone/celular/WhatsApp, CPF/documento/RG, pet/animal e vaga/estacionamento/garagem.

Se não encontra o cabeçalho de bloco/nome, o parser usa colunas posicionais e defaults (“1” e “Sem Nome”). Divide cada linha por vírgula ou ponto e vírgula e remove aspas externas simples. Esse parser não implementa o padrão CSV completo: campos entre aspas contendo vírgula/ponto e vírgula, aspas escapadas e quebras de linha dentro de campos podem ser interpretados incorretamente.

## Contrato backend Shadow

- `GET /api/v1/moradores?bloco=&busca=` — `moradores:read`.
- `POST /api/v1/moradores` — `moradores:create`.
- `PUT /api/v1/moradores/{id}` — `moradores:update`.
- `DELETE /api/v1/moradores/{id}` — `moradores:delete`.
- `POST /api/v1/moradores/importar` — `moradores:import`.

Schema:
- Obrigatórios: `bloco`, `apartamento`, `nome`.
- Opcionais: `email`, `telefone`, `cpf`, `petNome`, `vagaGaragem`.
- Campos string são aparados; campos extras são recusados.
- `MoradorImport` mantém defaults de bloco “1” e nome “Sem Nome”.

Admin e Operador possuem leitura, criação, edição, exclusão e importação no catálogo de capacidades atual. A autorização real continua no servidor e exige principal autenticado e ativo.

## Persistência

O adapter `PostgresMoradoresRepository` usa `bravo_shadow.moradores` e mapeia os nove campos do contrato. A factory seleciona o adapter quando o backend é explicitamente PostgreSQL; o padrão memória é volátil. Nenhuma base foi conectada ou migration aplicada nesta etapa.

## Estrutura visual criada

- Formulário com os oito campos funcionais do legado.
- Filtros por bloco e por nome/apartamento.
- Tabela com colunas correspondentes à listagem original.
- Área de importação CSV/TXT com aviso de validação e confirmação pendentes.
- Alertas de privacidade para CPF/RG e contatos.
- Estados vazios sem dados inventados.

Os campos, botões e seletor de arquivo estão desabilitados. Não há chamadas de rede, leitura de dados pessoais ou gravações.

## Lacunas e riscos

1. **Importação não atômica:** o service atual percorre o lote e insere um item por vez. Uma falha intermediária pode deixar importação parcial.
2. **Sem relatório por linha:** a resposta informa somente a quantidade importada; não identifica linhas inválidas, duplicadas ou rejeitadas.
3. **Sem deduplicação:** não há regra para detectar unidade já cadastrada, pessoa repetida ou CPF/RG duplicado.
4. **Unidade sem entidade própria:** bloco/apartamento são strings no registro, sem FK/registro de unidades nem restrição única demonstrada.
5. **Sem paginação:** o adapter lista a coleção inteira; filtros são aplicados no service após carregar todos os registros.
6. **Busca limitada:** o backend pesquisa somente nome e apartamento, além do filtro por bloco; não pesquisa e-mail, telefone ou CPF.
7. **Exclusão física:** não foi identificada inativação, histórico ou trilha de exclusão no fluxo atual.
8. **Dados pessoais:** CPF/RG, e-mail e telefone exigem acesso mínimo, proteção de logs e exportação controlada. Não usar dados reais em preview/homologação.
9. **Validação:** e-mail é tipado como string no schema (sem validação EmailStr); CPF/RG e telefone preservam formato textual sem validação, por compatibilidade com o legado.
10. **CSV:** parser legado simples não é adequado para CSV arbitrário; a migração deve adotar parser compatível e prévia antes de submeter o lote.
11. **Permissões:** Operador tem exclusão e importação no catálogo atual. Confirmar se isso corresponde à política operacional antes de ativar ações.

## Próximos passos

1. Criar importação em duas fases: prévia/validação e confirmação explícita.
2. Implementar parser CSV correto, limites de arquivo/lote, normalização e resultado por linha.
3. Garantir transação única para o lote e idempotência/deduplicação com regra aprovada.
4. Definir a identidade da unidade e regra de unicidade por condomínio.
5. Adicionar paginação e filtros eficientes no repositório.
6. Definir política de exclusão/inativação e histórico.
7. Revisar permissões de exclusão/importação para Operador.
8. Integrar Google/Bearer e homologar apenas com dados sintéticos.

## Situação

- [x] Campos, filtros, ações e importação legados identificados.
- [x] Schema, rotas, capacidades e adapter PostgreSQL inspecionados.
- [x] Tela Shadow própria criada, sem dados fictícios ou chamadas.
- [x] README e matriz de equivalência atualizados.
- [ ] Importação transacional, validada e com relatório por linha.
- [ ] Regra de unidade única/deduplicação aprovada.
- [ ] Paginação, histórico e política de exclusão.
- [ ] Revisão de permissões e privacidade.
- [ ] Integração Google/Bearer e homologação isolada.

**Status: estrutura funcional mapeada; operações e importação continuam bloqueadas até autenticação, privacidade e integridade do lote serem resolvidas.**
