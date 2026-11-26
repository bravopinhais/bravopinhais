# Mapa de dados do legado — Bravo

## Finalidade

Registrar a estrutura de armazenamento observável no código original, como insumo da Fase 0 da migração. Este documento descreve **formato e estrutura**, não contém exportação de dados reais e não autoriza conexão, extração ou escrita em produção.

## Baseline examinada

- Repositório: `bravopinhais/bravopinhais`
- Branch do legado: `upgrade/project-hardening`
- Arquivo: `index.html`
- SHA observado: `873dbf37bbcf2082faa0444ac28cb9ca9f8ff21c`
- Área examinada: inicialização de dados, leitura/gravação em nuvem, cache local, backup/restauração e renderizadores de módulos.

## 1. Modelo de persistência legado

O legado usa um **documento JSON agregado**, e não uma tabela relacional por módulo no código do frontend:

- Tabela Supabase referenciada: `public.condominio_dados`.
- Identificador lógico utilizado: `id = 'principal'`.
- Leitura: seleciona a coluna `payload` para esse identificador.
- Gravação: `upsert` de `id`, `payload` e `atualizado_em`.
- Atualização em tempo real: canal Supabase escuta eventos da tabela `condominio_dados`, filtrados por `id=eq.principal`.
- Cache de navegador: `localStorage` sob a chave `guardioes_bravo_db`.
- Backup/restauração: JSON completo do objeto agregado.
- Exportação CSV: exporta coleções selecionadas; remove campos binários compactados de foto/arquivo do CSV.

**Implicação:** o payload é a unidade de leitura/gravação do legado. Migrar cada coleção isoladamente exige primeiro definir um snapshot consistente, transformar os dados e reconciliar o resultado. Não se deve interpretar os nomes das propriedades JSON como prova de que existam tabelas Supabase com os mesmos nomes.

## 2. Coleções e objetos de primeiro nível

As propriedades observadas na inicialização do objeto de dados incluem:

| Chave JSON | Tipo observado | Domínio | Observações |
|---|---|---|---|
| `condominio` | objeto | Cadastro institucional | Dados cadastrais, endereço/contato e identificadores de concessionárias/unidades consumidoras |
| `conselheiros` | lista | Conselho | Registros individuais do corpo diretivo |
| `usuarios` | lista | Usuários | Conta, identificação, e-mail, cargo/loja, perfil e status; o legado também contém propriedades de autenticação antigas |
| `plano_contas` | lista | Plano de Contas | Código, nome e tipo aparecem nos registros iniciais |
| `financeiro` | lista | Contas a pagar/receber | Coleção própria dentro do payload |
| `formas_monetarias` | lista | Formas Monetárias | Coleção própria |
| `contas_bancarias` | lista | Contas Bancárias/Caixa | Coleção própria |
| `moradores` | lista | Moradores/Unidades | Coleção própria; há importação de planilha |
| `fornecedores` | lista | Fornecedores | CNPJ e razão social aparecem no formulário |
| `empregados` | lista | Empregados | Nome, cargo, empresa, endereço, telefone e contato de emergência aparecem no formulário |
| `categorias` | lista | Pastas Gerais | Registros com identificador e nome |
| `estoque` | lista | Estoque | Registros de produtos; há foto compactada |
| `acertos_estoque` | lista | Movimentações de estoque | Histórico separado da coleção de produtos |
| `motivos_acerto_estoque` | lista | Motivos de acerto | Registros com identificador e nome |
| `documentos` | lista | Documentos | Há arquivo compactado e metadados de nome |
| `logs` | lista | Logs | Conteúdo e finalidade ainda precisam de inventário específico |

A inicialização também contém dados padrão demonstrativos. Esses valores não devem ser tratados como dados reais, nem usados como fonte de importação.

## 3. Campos já observados em formulários

Este é um inventário parcial baseado nos campos visíveis nos formulários e renderizadores examinados. Não é ainda um esquema completo nem substitui a extração de todos os campos de cada modal.

| Domínio | Campos observados | Status do inventário |
|---|---|---|
| Condomínio | nome, CNPJ, razão social, endereço, bairro, cidade, UF, CEP, telefone, e-mail; Copel por bloco e áreas comuns; gás do salão; Sanepar | Parcial; confirmar campos opcionais e validações |
| Conselho | nome, cargo, bloco/apartamento | Parcial; conferir demais campos e regras |
| Usuários | identificador, usuário/login legado, nome, e-mail, cargo, loja/unidade, perfil, status, primeiro acesso e campos antigos de senha | Parcial; propriedades de senha são legado e não podem ser reintroduzidas no novo fluxo |
| Plano de Contas | id, código, nome, tipo (Receita/Despesa nos exemplos iniciais) | Parcial; confirmar hierarquia, natureza e exclusões |
| Fornecedores | id, CNPJ, razão social | Formulário observado; verificar campos adicionais em outras rotas |
| Empregados | id, nome, cargo, empresa, endereço, telefone, nome do contato de emergência, telefone de emergência | Formulário observado |
| Categorias/Pastas | id, nome | Formulário observado; confirmar se há metadados adicionais |
| Motivos de acerto | id, nome | Formulário observado |
| Estoque | há identificador, nome/código e dados de produto; marca, linha, fabricante, data de cadastro, foto compactada aparecem no contrato Shadow e precisam ser comparados campo a campo com o legado | Pendente de extração completa |
| Documentos | pasta, título/nome do arquivo e conteúdo compactado são referências presentes nos fluxos; confirmar MIME, extensão, tamanho e demais metadados | Pendente de extração completa |
| Financeiro | tipo Receber/Pagar, histórico, valor e referência opcional ao plano de contas estão no contrato Shadow; não assumir equivalência integral ao legado | Pendente de extração do formulário legado |
| Formas Monetárias | nome aparece no fluxo conectado do Shadow; confirmar o formulário original e eventuais atributos adicionais | Pendente |
| Contas Bancárias | formulário original existe; inventariar todos os campos e semântica do saldo | Pendente |
| Moradores | formulário e importador de planilha existem; inventariar todos os campos sem copiar dados pessoais | Pendente |
| Acertos de Estoque | produto, tipo, quantidade, motivo e documento são elementos a verificar no formulário completo e no modelo de persistência | Pendente de extração completa |

## 4. Identificadores e relacionamentos: o que sabemos e o que falta

### Observado

- Os registros das coleções usam identificadores `id` no frontend.
- Há referência entre lançamentos financeiros e Plano de Contas no contrato Shadow.
- Acertos de estoque afetam a quantidade do produto e mantêm histórico separado.
- Categorias e motivos de acerto são coleções distintas, embora apareçam na mesma tela de Pastas & Categorias.
- Documentos podem ser associados a pastas/categorias, mas a cardinalidade e a regra exata ainda precisam ser verificadas.
- O backup JSON preserva o objeto agregado inteiro.

### Ainda não comprovado

- Se os IDs são globalmente únicos ou apenas únicos dentro de cada coleção.
- Se todos os relacionamentos usam IDs ou se há vínculos por texto/código.
- Se existem referências órfãs ou duplicadas no conjunto real.
- Se exclusões em cascata, restrições ou bloqueios são aplicados de forma consistente no legado.
- Se há tabelas auxiliares no Supabase além de `condominio_dados`.
- Se o Realtime é usado por outros clientes ou somente pela aplicação observada.

## 5. Riscos para a transformação relacional

1. **Snapshot inconsistente:** o documento agregado pode mudar enquanto a extração é realizada. A migração futura precisa de janela/snapshot controlado e versão ou timestamp de referência.
2. **Escrita concorrente:** o legado atualiza o payload inteiro. Uma gravação concorrente pode sobrescrever mudanças de outro usuário se não houver controle de versão adequado.
3. **IDs e duplicidade:** antes de criar chaves estrangeiras, validar unicidade, referências e normalização de IDs.
4. **Dados pessoais:** moradores, usuários, empregados, contatos e documentos exigem minimização, acesso restrito e política de retenção.
5. **Credenciais antigas:** não migrar hashes, senhas, tokens ou segredos do legado para o novo modelo. A autenticação vigente do Bravo é por conta Google/e-mail validada no servidor.
6. **Arquivos compactados:** preservar bytes/conteúdo original durante a primeira transformação; decodificação, armazenamento externo e conversão devem ser etapas separadas e testadas.
7. **Defaults demonstrativos:** não importar dados padrão do código como se fossem registros operacionais.
8. **Logs:** identificar se são eventos de auditoria, mensagens de interface ou histórico funcional antes de decidir destino.

## 6. Estratégia recomendada de migração de dados

1. Aprovar o inventário estrutural e completar os campos de cada coleção.
2. Obter, em ambiente autorizado e separado, um snapshot de teste sintético/anonimizado do payload, sem credenciais ou dados pessoais desnecessários.
3. Definir um mapeamento explícito: chave JSON → tabela destino → coluna → tipo → transformação → regra de validação.
4. Construir importador idempotente que não altere a origem e gere relatório por coleção: lidos, importados, rejeitados, duplicados e referências não resolvidas.
5. Fazer dry-run e reconciliação de contagens, IDs, somas e vínculos antes de qualquer carga real.
6. Ensaiar rollback e repetição da carga em banco local descartável.
7. Só propor piloto de dados reais após aprovação formal, backup verificável, controle de acesso e plano de retorno.

## 7. Próxima etapa da Fase 0

Completar a ficha técnica por coleção, começando por **Condomínio & Conselho** e **Plano de Contas**, e depois avançar para os domínios de menor dependência. Para cada uma, registrar:

- campos de formulário e tipos;
- obrigatoriedade, normalização e validações;
- operações de criar/editar/excluir;
- identificadores e referências;
- regras de exclusão e integridade;
- importação/exportação e arquivos;
- contrato equivalente no Shadow;
- testes e evidências ainda ausentes.

**Limite desta entrega:** somente leitura do código e documentação. Nenhum dado real foi extraído; nenhuma tabela, migration, política, aplicação ou banco foi alterado.
