# Revisão consolidada de dependências — Fase 0 da migração

**Branch:** `bravo-shadow`  
**Natureza:** consolidação documental; não é autorização de carga, corte ou alteração funcional.  
**Baseline do legado:** `index.html`, SHA `873dbf37bbcf2082faa0444ac28cb9ca9f8ff21c`.

## 1. Objetivo e documentos de referência

Consolidar o que foi identificado nas fichas técnicas dos lotes 01 a 06 e propor uma ordem segura de importação. Esta revisão trata de estrutura, dependências e lacunas de contrato; não consultou payload real nem banco de produção.

Fichas consideradas:
- `ficha-tecnica-colecoes-fase0-01.md`: Condomínio, Conselho e Plano de Contas.
- `ficha-tecnica-colecoes-fase0-02.md`: Financeiro, Formas Monetárias e Contas Bancárias.
- `ficha-tecnica-colecoes-fase0-03.md`: Moradores, Fornecedores e Empregados.
- `ficha-tecnica-colecoes-fase0-04.md`: Categorias e Motivos de Acerto.
- `ficha-tecnica-colecoes-fase0-05.md`: Estoque, Acertos e Motivos.
- `ficha-tecnica-colecoes-fase0-06.md`: Documentos e vínculo com Categorias.

## 2. Mapa consolidado de dependências

| Domínio / coleção | Depende de | Quem depende dele | Observação para a carga |
|---|---|---|---|
| Condomínio | Nenhuma coleção de negócio identificada | Dados institucionais e telas relacionadas | Preservar campos não exibidos no formulário; não reduzir o objeto aos campos visíveis. |
| Conselho | Nenhuma FK explícita encontrada para Condomínio | Exibição conjunta na tela institucional | `db.conselheiros` e `db.condominio` são gravados separadamente; não criar FK sem payload adicional que a comprove. Preservar `BlocoAp`. |
| Categorias / Pastas Gerais | Nenhuma | Documentos | Importar antes de documentos; legado guarda o nome da pasta, Shadow aceita `categoriaId` opcional. |
| Motivos de Acerto | Nenhuma | Acertos de Estoque | Importar antes dos acertos; legado grava texto do motivo, não ID. |
| Fornecedores | Nenhuma relação estrutural confirmada nesta inspeção | Possíveis fluxos financeiros/administrativos | Não criar FK por suposição; conferir uso real no restante do legado antes da carga. |
| Empregados | Nenhuma relação estrutural confirmada nesta inspeção | Possíveis fluxos administrativos | Dados de contato de emergência exigem proteção de acesso; não inventar campos trabalhistas ausentes. |
| Moradores | Nenhuma coleção/FK de Unidade encontrada | Dashboard e filtros de moradores | `bloco` e `apartamento` são campos textuais no próprio morador; não criar entidade Unidade por inferência. Preservar CPF/telefone como texto; importação CSV exige validação por linha. |
| Plano de Contas | Nenhuma | Financeiro; Relatórios/DRE | Importar antes de títulos financeiros; preservar `id` e `codigo` como texto. |
| Formas Monetárias | Nenhuma dependência estrutural comprovada | Fluxos financeiros (uso operacional a confirmar) | Importar como cadastro independente; não presumir vínculo com títulos sem evidência. |
| Contas Bancárias | Nenhuma dependência estrutural comprovada | Caixa/relatórios (uso operacional a confirmar) | Saldo é manual; não tratar como extrato nem conciliação. |
| Financeiro | Plano de Contas opcional por `planoContaId` | Dashboard e DRE | Contrato atual não contém datas, status de liquidação nem conta bancária; não reconstruir períodos/baixas inexistentes. |
| Estoque | Nenhuma coleção auxiliar estrutural obrigatória; cadastro de produtos | Acertos de Estoque | Importar IDs e saldo atuais antes dos movimentos; preservar imagens Gzip. |
| Acertos de Estoque | Estoque por `produtoId`; Motivos por texto `motivo` | Histórico e saldo de estoque | `produtoId` é FK lógica explícita; motivo é texto, não `motivoId`. Importar depois de produtos e motivos; manter movimentos imutáveis e reconciliar órfãos. |
| Documentos | Categorias por nome em `pasta` textual | Gestão documental e consultas | O formulário lista nomes de categorias e grava o nome em `pasta`; não existe FK de categoria no legado. Preservar texto e bytes Gzip; vínculo por ID apenas como extensão Shadow, se exato e único. |
| Dashboard | Dados dos módulos de origem | Visão geral | Não importar métricas calculadas como se fossem dados-base; reconstruir após fontes aceitas. |
| Relatórios / DRE | Financeiro e Plano de Contas; regras contábeis aprovadas | Gestão/decisão | Última camada; não produzir relatório por período sem campos temporais adequados. |
| Usuários / Identidade | Google ID token, cadastro interno, matriz de capacidades, auditoria | Todas as rotas de negócio | Pré-requisito transversal de segurança, não apenas uma coleção a importar. |

## 3. Ordem técnica recomendada para uma futura carga

A sequência abaixo respeita as dependências conhecidas. É uma proposta para ensaios locais e não autoriza extração ou migração real.

### Onda 0 — Preparação e segurança (bloqueante)
1. Congelar e registrar a versão exata do payload de origem por procedimento autorizado, sem expor dados pessoais em logs.
2. Definir inventário de coleções presentes, ausentes e vazias; distinguir dados persistidos de defaults/fallbacks de interface.
3. Aprovar autenticação, matriz de capacidades e auditoria antes de expor qualquer rota de negócio.
4. Preparar ambiente PostgreSQL local descartável, migrations revisadas, backup/restore e importador idempotente com modo dry-run.
5. Implementar caminho de importação que aceite IDs legados sem usar os endpoints normais de criação.

### Onda 1 — Cadastros independentes e referências
1. Condomínio.
2. Conselho.
3. Categorias / Pastas Gerais.
4. Motivos de Acerto.
5. Fornecedores.
6. Empregados.
7. Moradores.
8. Plano de Contas.
9. Formas Monetárias.
10. Contas Bancárias.

A ordem interna dos cadastros sem dependência confirmada pode ser ajustada por prioridade operacional. Categorias e Motivos devem preceder os domínios que os referenciam.

### Onda 2 — Domínios transacionais
1. Estoque (produtos, saldo atual, limites, etiquetas e fotos).
2. Financeiro (títulos, preservando referências opcionais ao Plano de Contas).
3. Documentos (após Categorias; preservar texto da pasta e arquivo).
4. Acertos de Estoque (somente depois de Estoque e Motivos; carregar histórico e reconciliar saldo).

**Atenção:** a ordem entre Financeiro, Documentos e Estoque pode ser ajustada operacionalmente, mas Acertos não podem preceder Estoque/Motivos e Documentos não devem preceder Categorias se for criada associação por ID.

### Onda 3 — Camadas derivadas
1. Dashboard, com métricas reconstruídas exclusivamente a partir de módulos migrados e aceitos.
2. Relatórios e DRE, após aprovação das regras contábeis e ampliação do modelo financeiro, se necessária.

## 4. Lacunas de equivalência que impedem uma carga cega

### 4.1 Identificadores e relacionamentos
- Os endpoints comuns do Shadow geram IDs novos para várias coleções. É necessário importador privilegiado e controlado para preservar IDs originais.
- Conselho e Plano de Contas possuem referências usadas por outras partes; preservar IDs é essencial.
- Financeiro usa `planoContaId` opcional; validar referências órfãs e manter títulos sem plano sem inventar associação.
- Documentos legados guardam `pasta` como texto; Shadow também admite `categoriaId`. Correspondência textual só pode ser convertida em vínculo quando for exata e única.
- Acertos legados guardam `produtoId` e texto `motivo`; o Shadow pode usar `motivoId`. Não resolver nomes ambíguos automaticamente.
- O legado pode conter movimentos apontando para produtos eliminados e documentos apontando para categorias removidas. Registrar órfãos sem descartá-los.

### 4.2 Campos e semântica não equivalentes
- Condomínio: preservar atributos institucionais que não aparecem no formulário atual.
- Conselho: manter exatamente `BlocoAp`, sem renomear ou normalizar durante a carga.
- Financeiro: faltam datas, competência, vencimento, baixa/liquidação, status e vínculo com conta bancária; relatórios temporais e conciliação não são equivalentes.
- Formas Monetárias: significado e faixa de `multaPct` precisam de regra documentada; não inferir relação automática com títulos.
- Contas Bancárias: `saldo` representa valor manual/saldo inicial, não extrato conciliado.
- Moradores: CPF, telefone, bloco e apartamento devem continuar texto; preservar zeros à esquerda e pontuação.
- Estoque: `marca`, `linha`, `fabricante` e `dataCadastro` existem no Shadow, mas não foram encontrados no objeto legado observado; não preencher com dados fictícios.
- Acertos: data legada é texto local pt-BR, Shadow usa timestamp; preservar texto original e não presumir UTC.
- Documentos e fotos: Base64 Gzip deve ser preservado integralmente; não recompactar durante a migração.

### 4.3 Regras de negócio divergentes
- Legado permite confirmar saída de estoque que gere saldo negativo; Shadow bloqueia saída acima do saldo. A política futura precisa ser aprovada sem alterar retroativamente o histórico.
- Legado permite apagar acerto sem reverter saldo; Shadow trata movimentos como imutáveis e exige compensação. Carga deve preservar histórico, não repetir exclusões.
- Categorias e motivos podem ser excluídos no legado sem preservar referências; Shadow adiciona bloqueios de exclusão.
- Dashboard/DRE não podem ser considerados equivalentes enquanto as fontes e regras temporais/contábeis não forem suficientes.

### 4.4 Segurança e privacidade
- Moradores, empregados, contatos de emergência e documentos podem conter dados pessoais. A carga de ensaio deve usar dados sintéticos ou anonimizados e acesso restrito.
- Nenhuma rota de negócio deve ser exposta antes de validar Google token, vínculo com usuário Bravo, capacidades aprovadas e auditoria.
- O desenho atual de RLS/roles ainda precisa de validação em PostgreSQL local; não usar privilégios de superusuário ou BYPASSRLS para contornar políticas.

## 5. Controles obrigatórios por coleção

Para cada coleção, o importador deverá gerar relatório com:
- contagem de origem e destino;
- IDs ausentes, duplicados e preservados;
- campos ausentes, extras e transformados;
- referências válidas, órfãs e ambíguas;
- valores inválidos sem descarte silencioso;
- resultado da validação de anexos/arquivos;
- reconciliação de saldos e totais quando aplicável;
- hash do lote, versão do importador e resultado da execução.

A carga deve ser idempotente: repetir o mesmo lote não pode duplicar registros nem criar IDs diferentes. A operação deve ser transacional por lote/domínio, com relatório de falhas e rollback testado.

## 6. Portões antes de qualquer carga real ou cutover

Nenhuma carga real será considerada autorizada até que todos os itens abaixo estejam comprovados:

- [ ] A origem de dados e o payload efetivo foram identificados por procedimento autorizado.
- [ ] Inventário distingue coleção ausente, vazia, dados reais e defaults/fallbacks.
- [ ] Importador preserva IDs e é idempotente.
- [ ] Mapeamento de relacionamentos e política de órfãos foi aprovado.
- [ ] Datas, decimais, textos e arquivos foram validados em ensaio local.
- [ ] PostgreSQL local, migrations, RLS, roles e políticas foram testados.
- [ ] Testes automatizados e integração executados com evidência.
- [ ] Autenticação Google, matriz de capacidades e auditoria foram aprovadas e aplicadas às rotas.
- [ ] Backup, restauração, reconciliação e rollback foram ensaiados.
- [ ] Responsável operacional aprovou janela e critérios de corte.

## 7. Conclusão e próximo trabalho

As coleções mapeadas permitem desenhar a sequência de importação, mas ainda não permitem executar uma carga confiável. Os maiores bloqueios são preservação de IDs, reconciliação do saldo de estoque, conversão segura de vínculos textuais para IDs, arquivos Gzip, lacunas temporais do Financeiro e segurança transversal.

**Próximo passo recomendado:** concluir a Fase 0 com uma ficha de importação por domínio que defina chave, transformação, estratégia de upsert, idempotência, validação e relatório de reconciliação. Começar pelo conjunto cadastral independente em ambiente local descartável; não acessar nem alterar produção.


## 8. Matriz de relacionamentos — evidência e tratamento na migração

Esta matriz separa referências identificadas nos contratos/fichas de relações que ainda não foram comprovadas. “Não confirmado” significa que o importador não pode criar FK, inferir cardinalidade ou preencher vínculo por semelhança de nome.

| Origem | Destino | Campo/forma observada | Grau de evidência | Regra para importação |
|---|---|---|---|---|
| Financeiro | Plano de Contas | `planoContaId` opcional no Shadow; a ficha confirma referência financeira | Confirmado no contrato Shadow; cardinalidade exata ainda não formalizada | Preservar o ID legado quando existir; validar destino. Se ausente, manter sem vínculo. Se órfão, registrar erro de reconciliação sem descartar o título. |
| Documento | Categoria/Pasta | Legado: `pasta` textual; Shadow: `categoriaId` opcional | Texto legado confirmado; FK é extensão Shadow | Preservar sempre o texto original. Criar FK somente com correspondência textual exata e única. Em zero ou múltiplas correspondências, manter FK nula e registrar pendência. |
| Acerto de Estoque | Produto/Estoque | `produtoId` no movimento legado | Confirmado na ficha do lote 05 | Importar produtos antes dos movimentos. Preservar ID; não remapear por nome. Movimento com produto ausente é órfão e deve permanecer no relatório de exceções. |
| Acerto de Estoque | Motivo de Acerto | Legado: texto `motivo`; Shadow: `motivoId` opcional | Texto legado confirmado; vínculo por ID é extensão Shadow | Preservar texto original. Associar ID somente quando a correspondência for exata e única; não normalizar para forçar associação. |
| Conselho | Condomínio | Contexto institucional sugerido pela estrutura e telas | Relação estrutural não comprovada por FK nesta revisão | Não criar FK nem impor cardinalidade até confirmar no payload e nas operações do legado. Preservar registros e campos integralmente. |
| Morador | Unidade/Bloco | Campos de bloco/apartamento aparecem como dados textuais na ficha/auditoria | Não foi comprovada coleção independente de unidades nem FK | Preservar bloco/apartamento como texto, inclusive zeros e pontuação. Não criar tabela de unidades nem vínculo automático nesta etapa. |
| Financeiro | Conta Bancária | Nenhum campo de conta bancária no contrato Financeiro atual | Não confirmado / ausente no contrato observado | Não associar título a conta bancária por forma monetária, histórico ou proximidade de cadastro. |
| Financeiro | Forma Monetária | Não foi comprovada FK no contrato observado | Não confirmado | Importar o cadastro independente; não inferir vínculo com títulos. |
| Dashboard/Relatórios/DRE | Financeiro e Plano de Contas | Agregações derivadas; DRE agrupa por conta vinculada | Dependência de leitura confirmada pela auditoria funcional | Reconstruir indicadores a partir das fontes aceitas. Não importar números agregados como registros-base. Títulos sem conta entram nos totais gerais, mas não nas linhas agrupadas por conta. |
| Usuário autenticado | Perfil interno Bravo | E-mail verificado do Google associado ao perfil interno | Regra de identidade vigente; não é relacionamento de migração de domínio | Resolver por e-mail verificado normalizado e único. Não importar senha/hash legado, nem tratar `perfil` como autorização até capacidades serem aprovadas. |

### Regras transversais de integridade

1. **Preservar chaves:** IDs legados são identificadores opacos; não converter para inteiro, UUID novo ou slug sem contrato explícito.
2. **Não inventar relações:** nomes iguais, textos parecidos, mesmo bloco ou mesma forma monetária não provam identidade referencial.
3. **Separar ausência de dado de ausência de relação:** campo inexistente no payload não deve ser preenchido com valor padrão; campo vazio não autoriza inferência.
4. **Registrar órfãos sem perda:** cada referência inválida deve aparecer no relatório com coleção, ID do registro, campo, valor original e decisão pendente, sem copiar dados pessoais para logs gerais.
5. **Não confundir agregação com vínculo:** Dashboard e DRE são consumidores de leitura, não pais de registros transacionais.
6. **Cardinalidade pendente:** onde a ficha não comprova 1:1, 1:N ou N:N, o importador deve validar apenas a referência individual e deixar a cardinalidade para contrato aprovado.

### Portão de aprovação desta matriz

O mapa está consolidado em nível estrutural, mas **não está aprovado para carga**. Para liberar um importador por domínio ainda será necessário conferir o payload autorizado e os pontos de leitura/escrita do legado, formalizar cardinalidades, decidir tratamento de cada classe de órfão e testar reconciliação com dados sintéticos. Nenhuma dessas etapas exige ou autoriza conexão com produção.


## 9. Evidência direta no legado — revisão de hipóteses

A inspeção dos formulários e funções de gravação do baseline foi consolidada em `evidencias-relacionamentos-legado-fase0.md`. Ela confirmou três referências usadas pelo código: Financeiro → Plano de Contas (`planoContaId`), Acerto de Estoque → Produto (`produtoId`) e Documentos → Categorias por nome textual (`pasta`). Também esclareceu que Conselho/Condomínio não têm FK explícita no código observado, Moradores guardam bloco/apartamento como texto, e Acertos guardam motivo como texto. Não foi encontrada associação Financeiro → Conta Bancária ou Forma Monetária.

Esta evidência corrige as hipóteses da tabela inicial: associação visual ou dependência de consulta não equivale a relacionamento referencial. O documento de evidências registra as linhas do código-fonte para cada conclusão. Ainda é necessário confrontar com o payload persistido autorizado, pois campos históricos ou extensões da instalação ativa podem não aparecer nos formulários atuais.
