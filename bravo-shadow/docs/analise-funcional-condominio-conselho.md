# Análise funcional — Condomínio & Conselho

Data: 2026-11-27  
Escopo: inspeção estática do módulo legado, schemas, serviços, routers e adapters PostgreSQL Shadow.

## Fluxo legado identificado

A tela `renderCondominioView` reúne duas áreas.

### Informações do condomínio e concessionárias

O formulário legado apresenta nome, CNPJ, telefone e e-mail, além de identificadores de consumo:
- Copel — Blocos 1, 2, 3 e 4;
- Copel — Áreas comuns;
- Registro de gás do salão;
- Registro Sanepar (água).

O schema Shadow também contempla razão social, endereço, bairro, cidade, UF e CEP. A tela Shadow inclui esses campos adicionais já previstos no contrato, sem criar campos novos no backend.

A atualização do legado salva os dados institucionais como um objeto único. O backend Shadow modela o condomínio como singleton.

### Corpo diretivo

A tabela do legado exibe Nome, Cargo, Bloco/Ap e ações. O modal de inclusão/edição contém:
- Nome (obrigatório);
- Cargo (obrigatório; novo registro inicia com “Síndico”);
- Bloco/Ap;
- Telefone.

O fluxo legado permite editar e excluir integrantes. O contrato Shadow contém os mesmos quatro campos.

## Contrato backend Shadow

### Condomínio

- `GET /api/v1/condominio` — capacidade `condominio:read`.
- `PUT /api/v1/condominio` — capacidade `condominio:update`.

Campos aceitos: `nome`, `cnpj`, `razaoSocial`, `endereco`, `bairro`, `cidade`, `uf`, `cep`, `telefone`, `email`, `copelBloco1` a `copelBloco4`, `copelAreasComuns`, `gasSalao`, `sanepar`. Strings são aparadas; campos extras são recusados.

O service atual lê e atualiza o registro `singleton`. O router não expõe ETag/If-Match nem versão esperada para atualização concorrente.

### Conselho

- `GET /api/v1/conselheiros` — `conselheiros:read`.
- `POST /api/v1/conselheiros` — `conselheiros:create`.
- `PUT /api/v1/conselheiros/{id}` — `conselheiros:update`.
- `DELETE /api/v1/conselheiros/{id}` — `conselheiros:delete`.

Schema: `nome` e `cargo` obrigatórios; `BlocoAp` e `telefone` opcionais, com strings aparadas. Admin possui CRUD; Operador possui leitura.

## Persistência

Há adapters PostgreSQL dedicados:
- `PostgresCondominioRepository`, tabela `bravo_shadow.condominio`;
- `PostgresConselheirosRepository`, tabela `bravo_shadow.conselheiros`.

O storage factory escolhe esses adapters quando o backend é PostgreSQL e exige conexão explicitamente configurada. O padrão memória usa repositórios em memória. Nenhum banco foi conectado ou migration aplicada nesta etapa.

## Estrutura visual criada

- Formulário institucional com todos os 17 campos do schema.
- Agrupamento visual de dados cadastrais, contato e unidades consumidoras.
- Formulário de inclusão de conselheiro com nome, cargo, bloco/apartamento e telefone.
- Tabela de composição do conselho.
- Avisos de permissões, autenticação pendente e limites do contrato.

Os campos e botões estão desabilitados. Não há requests de leitura ou gravação e nenhum dado de exemplo é exibido. A tela só poderá ser ativada quando o cliente usar a sessão Google e enviar o ID token como Bearer em cada chamada.

## Lacunas e riscos

1. O endpoint singleton não expõe controle de concorrência (ETag/If-Match); atualizações simultâneas podem sobrescrever alterações.
2. Os serviços e adapters atuais não demonstram auditoria de negócio transacional específica para alteração institucional ou CRUD do conselho.
3. O contrato não modela mandato, datas de início/fim, atas, eleição, anexos, suplentes ou histórico de composição.
4. O schema não valida formalmente CNPJ, CEP, telefone ou e-mail; não adicionar validações restritivas sem comparar o legado e homologar.
5. A exclusão de conselheiro é física; não foi identificada política de retenção/histórico.
6. O contrato do condomínio permite patch parcial, mas o router não exige versão esperada.
7. A leitura singleton pode precisar de um registro inicial; não inserir valores fictícios nem inicializar com dados de produção.

## Próximos passos

1. Adicionar auditoria transacional para alteração do condomínio e operações do conselho.
2. Introduzir controle de concorrência no singleton (versão/If-Match) antes de habilitar gravações.
3. Definir política de histórico/inativação para conselheiros e exclusão.
4. Confirmar se mandato, atas ou anexos são recursos usados no sistema atual; não presumir.
5. Integrar Google/Bearer e persistência PostgreSQL isolada.
6. Homologar os 17 campos e as operações do conselho com dados sintéticos.

## Situação

- [x] Fluxo legado e campos identificados.
- [x] Schema e rotas inspecionados.
- [x] Adapters PostgreSQL identificados.
- [x] Tela Shadow própria criada sem dados fictícios nem chamadas.
- [x] Matriz de equivalência atualizada.
- [ ] Auditoria transacional e concorrência.
- [ ] Política de retenção do conselho.
- [ ] Integração Google/Bearer e homologação isolada.

**Status: estrutura cadastral mapeada; gravações bloqueadas até autenticação, auditoria e concorrência serem resolvidas.**
