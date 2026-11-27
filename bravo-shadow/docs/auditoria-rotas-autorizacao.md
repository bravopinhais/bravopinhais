# Auditoria de rotas e autorização funcional — Bravo Shadow

## Resultado executivo

Revisão estática dos 15 arquivos `router.py` e de `backend/app/main.py`, na branch `bravo-shadow`.

**Estado atual corrigido (27/11/2026):** a inspeção da branch confirma que as rotas de negócio agora declaram dependências de capacidade por endpoint, e essas dependências obtêm um principal por meio da validação do ID token Google. O teste `test_every_business_api_route_requires_google_identity` verifica a cobertura de identidade; `test_every_business_api_route_has_capability_gate_or_is_identity_endpoint` verifica a cobertura de capacidade. A política `ROLE_CAPABILITIES` concede conjunto vazio tanto a `Admin` quanto a `Operador`; portanto, a proteção está ativa em modo *fail-closed*, mas nenhuma operação de negócio é autorizada até a aprovação explícita da matriz funcional.

O endpoint `GET /api/v1/health` é público por desenho e informa apenas estado/configuração do serviço. Deve continuar sem dados sensíveis.

Esta auditoria é estática; não executou requisições HTTP nem testes de penetração.

## Inventário de rotas e operações observadas

| Módulo | Prefixo | Operações expostas atualmente |
|---|---|---|
| Plano de Contas | `/api/v1/plano-contas` | GET lista; POST cria; PUT altera; DELETE exclui |
| Financeiro | `/api/v1/financeiro` | GET lista; POST cria; PUT altera; DELETE exclui |
| Formas Monetárias | `/api/v1/formas-monetarias` | GET lista; POST cria; PUT altera; DELETE exclui |
| Contas Bancárias | `/api/v1/contas-bancarias` | GET lista; POST cria; PUT altera; DELETE exclui |
| Fornecedores | `/api/v1/fornecedores` | GET lista; POST cria; PUT altera; DELETE exclui |
| Empregados | `/api/v1/empregados` | GET lista; POST cria; PUT altera; DELETE exclui |
| Condomínio | `/api/v1/condominio` | GET cadastro; PUT altera |
| Conselheiros | `/api/v1/conselheiros` | GET lista; POST cria; PUT altera; DELETE exclui |
| Moradores | `/api/v1/moradores` | GET lista/filtro; POST cria; PUT altera; DELETE exclui; POST `/importar` |
| Categorias | `/api/v1/categorias` | GET lista; POST cria; DELETE exclui |
| Motivos de Acerto | `/api/v1/motivos-acerto-estoque` | GET lista; POST cria; DELETE exclui |
| Estoque | `/api/v1/estoque` | GET lista; POST cria; PUT altera; DELETE exclui |
| Acertos de Estoque | `/api/v1/acertos-estoque` | GET lista; POST registra movimento; DELETE rota legada, bloqueada com 409 em memória e PostgreSQL |
| Documentos | `/api/v1/documentos` | GET lista; GET por ID; POST cria; PUT altera; DELETE exclui |
| Usuários | `/api/v1/usuarios` | GET lista; GET por ID; POST cria; PUT altera; DELETE exclui |

## Situação atual da segurança HTTP

- As rotas de negócio declaram dependências centrais de capacidade; a dependência exige identidade Google validada e cadastro interno ativo antes de avaliar a capacidade.
- O router de identidade `GET /api/v1/auth/me` exige `get_current_principal`; `GET /api/v1/health` permanece público e não consulta dados de negócio.
- A resolução do principal valida claims do token Google, exige `sub`, e-mail verificado e exatamente um cadastro interno correspondente com status `Ativo`.
- O catálogo `CAPABILITIES` é granular, mas `ROLE_CAPABILITIES` concede atualmente capacidades vazias a `Admin` e `Operador`; assim, rotas de negócio autenticadas continuam respondendo 403 até aprovação da matriz.
- A conexão direta dos routers aos serviços em `request.app.state.services` não substitui a dependência de capacidade, que é avaliada antes do handler.
- Não introduzir login por senha local. O fluxo de identidade esperado continua sendo Google/e-mail com validação de token no servidor.
- CORS fechado não substitui autenticação; ocultar a interface também não protege endpoints.

## Classificação de sensibilidade e cautelas

| Área | Risco principal | Cautela mínima antes de uso real |
|---|---|---|
| Financeiro, plano de contas e bancos | Exposição e alteração de informação financeira | Exigir identidade válida; separar consulta de operações de escrita; auditar alterações |
| Moradores | CPF, telefone, e-mail, unidade e dados de pets | Acesso restrito, logs sem dados pessoais desnecessários e princípio do menor privilégio |
| Empregados | Endereço, telefone e contato de emergência | Acesso restrito e trilha de auditoria |
| Documentos | Conteúdo de arquivos e documentos administrativos | Restringir leitura e escrita por perfil; não expor armazenamento diretamente |
| Usuários | Gestão de perfis e status | Proteger criação/alteração/exclusão; impedir autoelevação de perfil |
| Estoque e acertos | Integridade de saldo e trilha de movimentos | Somente movimento cria variação de saldo; histórico persistido imutável |
| Condomínio e conselho | Dados administrativos e de contato | Separar consulta de alteração cadastral |

## Matriz funcional — proposta para discussão, ainda não aprovada

Não atribuir permissões automaticamente aos perfis existentes. A proposta abaixo é um desenho de menor privilégio para ser validado com o responsável pelo Bravo:

| Capacidade | Admin | Operador |
|---|---|---|
| Consultar módulos operacionais | A definir | A definir |
| Criar/editar cadastros operacionais | A definir | A definir |
| Excluir cadastros | A definir | A definir |
| Criar/alterar lançamentos financeiros | A definir | A definir |
| Consultar dados pessoais de moradores/empregados | A definir | A definir |
| Importar moradores em lote | A definir | A definir |
| Registrar entrada/saída de estoque | A definir | A definir |
| Corrigir movimento de estoque | Somente estorno compensatório futuro | Somente estorno compensatório futuro |
| Gerenciar usuários e perfis | A definir | A definir |
| Alterar dados institucionais do condomínio | A definir | A definir |
| Consultar/gerir documentos | A definir | A definir |

Os valores “A definir” são intencionais. Não foi encontrada regra funcional aprovada no backend que permita concluir o que Admin e Operador podem fazer. Não promover o valor `perfil` recebido do cliente como prova de autorização.

## Desenho técnico recomendado

1. Criar um componente central de autenticação para validar no servidor o token de identidade Google (assinatura, emissor, audiência, expiração e sujeito).
2. Não confiar em e-mail, perfil, cargo ou ID enviados no corpo/query/header pelo navegador.
3. Resolver o sujeito autenticado para um cadastro ativo em `usuarios`; normalizar e-mail e validar o vínculo de forma segura.
4. Criar dependências FastAPI centralizadas para obter o usuário autenticado e exigir capacidades específicas por endpoint.
5. Aplicar autorização por ação, não apenas por módulo: `ler`, `criar`, `editar`, `excluir`, `importar`, `gerenciar_usuarios`.
6. Negar por padrão quando não houver identidade válida, usuário inexistente/inativo ou capacidade não concedida.
7. Impedir que um usuário altere o próprio perfil/status ou crie um administrador sem autorização administrativa explícita.
8. Registrar auditoria de operações sensíveis com ator, ação, entidade, identificador, instante e resultado; evitar registrar tokens ou conteúdo pessoal.
9. Manter `/api/v1/health` público, sem revelar segredo, URL de banco ou dados de negócio.
10. Cobrir testes positivos e negativos para cada capacidade e para cada rota sensível.

## Relação com RLS e a role PostgreSQL

A role técnica compartilhada da API é um perímetro de serviço, não uma identidade individual. Policies RLS aplicadas somente à role da API não diferenciam Admin de Operador. A autorização por usuário precisa acontecer no backend, antes de chamar os serviços.

Não habilitar o modo PostgreSQL em ambiente acessível por usuários enquanto a autenticação e autorização HTTP estiverem ausentes. A futura role técnica deve continuar sem superuser e sem `BYPASSRLS`; não criar policies permissivas para contornar o problema.

## Próximas decisões necessárias

1. Confirmar a matriz de capacidades de Admin e Operador, especialmente financeiro, dados pessoais, exclusões e gestão de usuários.
2. Confirmar se existe mais de um nível operacional ou se os dois perfis atuais são suficientes.
3. Definir quais rotas exigem auditoria detalhada e retenção dos eventos.
4. Só depois implementar autenticação Google no backend e dependências de autorização, com testes de acesso negado.

## Estado desta etapa

- Revisados estaticamente os 15 routers e a montagem da aplicação.
- Nenhum endpoint foi alterado nesta etapa.
- Nenhum token ou credencial foi solicitado ou manipulado.
- Nenhuma migration, role, policy ou banco foi criado/alterado.
- O sistema original e seu `index.html` permanecem fora do escopo.


## Matriz provisória por módulo — política segura até aprovação

Como o repositório não contém uma matriz funcional aprovada para `Admin` e `Operador`, a regra técnica provisória recomendada é **negar por padrão**. Isso evita transformar suposições em permissões reais.

| Módulo | Admin autenticado e ativo | Operador autenticado e ativo | Observação |
|---|---|---|---|
| Dashboard | Consultar | Pendente de aprovação | Indicadores podem revelar dados financeiros e pessoais |
| Condomínio & Conselho | Consultar/criar/editar/excluir conforme rotas | Pendente de aprovação | Alteração institucional |
| Plano de Contas | Consultar/criar/editar/excluir | Pendente de aprovação | Impacta classificação financeira |
| Contas a Pagar / Receber | Consultar/criar/editar/excluir | Pendente de aprovação | Informação financeira sensível |
| Formas Monetárias | Consultar/criar/editar/excluir | Pendente de aprovação | Configuração que afeta cálculos |
| Contas Bancárias / Caixa | Consultar/criar/editar/excluir | Pendente de aprovação | Saldo e dados bancários |
| Moradores & Unidades | Consultar/criar/editar/excluir/importar | Pendente de aprovação | Contém dados pessoais |
| Fornecedores | Consultar/criar/editar/excluir | Pendente de aprovação | Dados cadastrais e fiscais |
| Empregados | Consultar/criar/editar/excluir | Pendente de aprovação | Dados pessoais e contatos de emergência |
| Pastas & Categorias | Consultar/criar/excluir conforme rotas | Pendente de aprovação | Cadastros de referência |
| Estoque & Inventário | Consultar/criar/editar/excluir conforme integridade | Pendente de aprovação | Saldo não pode ser alterado diretamente após histórico |
| Acerto de Estoque | Consultar e registrar movimentos | Pendente de aprovação | Histórico persistido sem UPDATE/DELETE |
| Gestão de Documentos | Consultar/criar/editar/excluir | Pendente de aprovação | Conteúdo documental |
| Relatórios & DRE | Consultar | Pendente de aprovação | Dados agregados podem revelar informação financeira |
| Gestão de Usuários | Consultar/criar/editar/excluir perfis | **Negado** | Exclusivo de administrador; proteger contra autoelevação |

**Interpretação:** “Pendente de aprovação” significa que a aplicação deve negar a ação até existir uma decisão explícita. Não significa que o Operador jamais poderá executar a ação. Depois de aprovada, a permissão deve ser atribuída por capacidade específica (por exemplo, `moradores:ler`, `estoque:registrar_movimento`) e não por uma regra genérica ampla.

### Regras invariáveis

- Usuário inexistente, inativo, sem token válido ou sem capacidade explícita: negar.
- O cliente não pode escolher o próprio perfil ou enviar permissões para elevar o acesso.
- Criação de usuário por endpoint público não pode criar Admin; a criação e promoção de Admin exigem fluxo administrativo protegido.
- Um usuário não pode alterar o próprio perfil ou status.
- O perfil `Admin` não pode alterar/apagar o histórico de movimentos persistidos de estoque; correções devem ser por movimento compensatório futuro.
- O health check permanece público e não expõe dados de negócio.
- A role PostgreSQL da API não decide entre Admin e Operador; essa decisão pertence ao backend autenticado.

### Recomendação para implementação posterior

Não adicionar ainda uma matriz hardcoded aos routers. Primeiro aprovar as capacidades do Operador; em seguida criar um catálogo central de permissões, testes unitários da política e testes HTTP para cada rota. A API deve aplicar a mesma política independentemente de a interface esconder ou mostrar um botão.


## Fundação técnica de autorização — implementada, ainda isolada

Foi criado `backend/app/core/authorization.py` com:

- catálogo explícito de capacidades por ação;
- principal imutável que representa identidade já autenticada;
- política provisória Admin/Operador;
- negação por padrão para usuário ausente/inativo, perfil desconhecido, identidade malformada ou capacidade desconhecida;
- resposta HTTP 403 quando a capacidade não é concedida.

Também foram adicionados testes unitários em
`backend/tests/test_authorization_policy.py` e instruções em
`backend/app/core/README-autorizacao.md`.

**Limite importante:** a política ainda não está conectada aos routers, não cria
sessões, não valida token Google e não consulta o cadastro. Nenhum endpoint
passou a exigir autenticação nesta entrega. O objeto `AuthenticatedPrincipal`
só poderá ser construído pela futura camada de autenticação após validar o
token e resolver o usuário ativo no banco.

O perfil Operador continua sem permissões concedidas até aprovação funcional.
A matriz do Admin é uma proposta técnica provisória e também deverá ser
confirmada antes da ativação. O catálogo não oferece edição/exclusão de
movimentos de estoque.

Nenhuma migration, role, policy PostgreSQL ou alteração no sistema original
foi feita nesta etapa.


## Mapa técnico de capacidades por endpoint — revisão estática

Este mapa foi elaborado conferindo os 15 arquivos `router.py` atuais.
Ele descreve a capacidade que deverá ser exigida quando a integração for
aprovada. **Não altera nem protege as rotas nesta etapa.**

| Módulo / método | Rota | Capacidade prevista |
|---|---|---|
| Plano de Contas — GET | `/api/v1/plano-contas` | `plano_contas:read` |
| Plano de Contas — POST | `/api/v1/plano-contas` | `plano_contas:create` |
| Plano de Contas — PUT | `/api/v1/plano-contas/{item_id}` | `plano_contas:update` |
| Plano de Contas — DELETE | `/api/v1/plano-contas/{item_id}` | `plano_contas:delete` |
| Financeiro — GET | `/api/v1/financeiro` | `financeiro:read` |
| Financeiro — POST | `/api/v1/financeiro` | `financeiro:create` |
| Financeiro — PUT | `/api/v1/financeiro/{item_id}` | `financeiro:update` |
| Financeiro — DELETE | `/api/v1/financeiro/{item_id}` | `financeiro:delete` |
| Formas Monetárias — GET/POST/PUT/DELETE | `/api/v1/formas-monetarias` e `/{item_id}` | `formas_monetarias:read/create/update/delete` conforme método |
| Contas Bancárias — GET/POST/PUT/DELETE | `/api/v1/contas-bancarias` e `/{item_id}` | `contas_bancarias:read/create/update/delete` conforme método |
| Fornecedores — GET/POST/PUT/DELETE | `/api/v1/fornecedores` e `/{item_id}` | `fornecedores:read/create/update/delete` conforme método |
| Empregados — GET/POST/PUT/DELETE | `/api/v1/empregados` e `/{item_id}` | `empregados:read/create/update/delete` conforme método |
| Condomínio — GET | `/api/v1/condominio` | `condominio:read` |
| Condomínio — PUT | `/api/v1/condominio` | `condominio:update` |
| Conselheiros — GET/POST/PUT/DELETE | `/api/v1/conselheiros` e `/{item_id}` | `conselheiros:read/create/update/delete` conforme método |
| Moradores — GET/POST/PUT/DELETE | `/api/v1/moradores` e `/{item_id}` | `moradores:read/create/update/delete` conforme método |
| Moradores — POST importar | `/api/v1/moradores/importar` | `moradores:import` |
| Categorias — GET/POST/DELETE | `/api/v1/categorias` e `/{item_id}` | `categorias:read/create/delete` conforme método |
| Motivos de Acerto — GET/POST/DELETE | `/api/v1/motivos-acerto-estoque` e `/{item_id}` | `motivos_estoque:read/create/delete` conforme método |
| Estoque — GET/POST/PUT/DELETE | `/api/v1/estoque` e `/{item_id}` | `estoque:read/create/update/delete` conforme método, sujeito às travas de integridade |
| Acertos de Estoque — GET | `/api/v1/acertos-estoque` | `acertos_estoque:read` |
| Acertos de Estoque — POST | `/api/v1/acertos-estoque` | `acertos_estoque:create` |
| Acertos de Estoque — DELETE legado | `/api/v1/acertos-estoque/{item_id}` | **Sem capacidade de exclusão**; bloqueio/409 em todos os modos, movimento imutável e correção futura por lançamento compensatório |
| Documentos — GET lista/por ID | `/api/v1/documentos` e `/{item_id}` | `documentos:read` |
| Documentos — POST/PUT/DELETE | `/api/v1/documentos` e `/{item_id}` | `documentos:create/update/delete` conforme método |
| Usuários — GET lista/por ID | `/api/v1/usuarios` e `/{item_id}` | `usuarios:read` |
| Usuários — POST/PUT/DELETE | `/api/v1/usuarios` e `/{item_id}` | `usuarios:create/update/delete`; exclusivo de fluxo administrativo aprovado |

### Pontos que exigem atenção antes da integração

1. As capacidades de CRUD acima já existem no catálogo central, mas os nomes
   `categorias` e `motivos_estoque` são diferentes dos nomes de tabelas
   SQL em alguns trechos. Manter um único identificador canônico no backend.
2. A rota de exclusão de acerto de estoque é legado: não criar capacidade para
   ela. O histórico de movimentos deve permanecer imutável.
3. A rota de gestão de usuários é especialmente sensível. A autorização para
   criar/editar/excluir usuários não deve permitir que o solicitante altere o
   próprio perfil/status nem promova a si mesmo.
4. O Dashboard ainda não possui endpoint de dados agregados identificado
   nesta revisão. A capacidade `dashboard:read` não deve ser confundida com
   acesso automático aos módulos de origem.
5. A rota de importação de moradores precisa de capacidade própria; não deve
   herdar automaticamente a permissão de criar um único morador.

### Critério de entrada em implementação

Antes de adicionar `Depends(require_capability_dependency(...))` às rotas,
aprovar explicitamente as permissões de Admin e Operador por ação. Em seguida,
integrar por módulo com testes HTTP de 401 (sem identidade), 403 (sem
capacidade), sucesso autorizado, usuário inativo e tentativa de autoelevação.


## Revisão de integridade de entrada do Financeiro

Na branch sombra, o schema financeiro agora remove espaços excedentes do
histórico e do identificador de Plano de Contas. Histórico composto apenas
por espaços é rejeitado com erro de validação (422). O identificador opcional
continua aceitando string vazia, preservando o contrato atual do sistema.

Foram adicionados três testes ao arquivo existente
`backend/tests/test_financeiro.py` para normalização do histórico,
rejeição de histórico em branco e normalização do vínculo com Plano de Contas.
Os testes ainda não foram executados neste ambiente.

A autorização dos módulos permanece pendente de aprovação da matriz de
permissões. Nenhuma rota de negócio foi ativada com a política provisória.


## Revisão de integridade do Plano de Contas e vínculo com Financeiro

A revisão estática confirmou que:

- O schema do Plano de Contas remove espaços excedentes de código e nome e rejeita valores vazios após a normalização.
- A aplicação verifica duplicidade de código sem diferenciar maiúsculas/minúsculas.
- O rascunho SQL define índice único em `lower(codigo)`, protegendo também contra duplicidade concorrente no PostgreSQL; o adaptador converte violação de unicidade em HTTP 409.
- O vínculo Financeiro → Plano de Contas é opcional, mas quando informado o PostgreSQL aplica chave estrangeira com `ON DELETE RESTRICT`.
- O serviço verifica referências financeiras antes da exclusão; sem verificador configurado, responde 503, e com referência existente responde 409.
- A atualização usa controle otimista de versão (`If-Match`/ETag).

Foram reforçados os testes de `backend/tests/test_plano_contas.py`: a duplicidade agora compara códigos alfanuméricos com diferenças de caixa, e foram incluídos casos de normalização de código/nome e rejeição de valores compostos apenas por espaços. Os testes ainda não foram executados.

O SQL continua sendo rascunho, não migration aplicada. A proteção efetiva no PostgreSQL só estará disponível depois de revisão e aplicação controlada da migration no ambiente local isolado. Nenhum banco foi conectado ou alterado nesta etapa.


## Revisão do vínculo entre Plano de Contas e Financeiro

- Os campos `codigo` e `nome` do Plano de Contas são normalizados pelo Pydantic (remoção de espaços externos) e rejeitam valores compostos apenas por espaços.
- A unicidade do código é verificada sem diferenciar maiúsculas/minúsculas no serviço; o banco também possui restrição de unicidade para proteger gravações concorrentes.
- A exclusão consulta o Financeiro e falha de forma fechada quando o verificador não está configurado; havendo vínculo, responde conflito. A chave estrangeira PostgreSQL com exclusão restrita permanece como segunda barreira no banco.
- O Financeiro agora delega a verificação ao método especializado `has_plan_account_reference` do repositório PostgreSQL (consulta `SELECT 1 ... LIMIT 1`), evitando carregar toda a coleção para uma simples checagem. No repositório em memória, usa a busca protegida pelo lock; adapters simples mantêm fallback compatível.
- A verificação de serviço e a restrição FK são salvaguardas complementares: a FK é a proteção definitiva contra exclusão concorrente no PostgreSQL.
- Teste automatizado foi acrescentado para confirmar que o serviço usa o verificador otimizado quando o adapter o disponibiliza. Os testes ainda precisam ser executados em ambiente Python e contra PostgreSQL local antes de considerar a integração validada.


## Revisão de integridade — Acerto de Estoque

A revisão da branch sombra identificou uma divergência entre os modos de armazenamento: PostgreSQL bloqueava a exclusão de movimentos, enquanto memória permitia apagar o registro sem reverter o saldo. O serviço agora responde 409 para exclusão de qualquer movimento existente nos dois modos; IDs inexistentes retornam 404. A rota permanece apenas por compatibilidade e não deve receber capacidade de exclusão.

Também foi alinhada a proteção do produto: quando existe movimento, a exclusão do produto é bloqueada e o PUT não pode alterar diretamente a quantidade. Alterações de descrição e metadados continuam permitidas se preservarem o saldo. O histórico e o saldo só mudam pelo fluxo de Entrada/Saída; correções futuras deverão usar movimento compensatório.

O schema normaliza produtoId, motivo e motivoId, rejeitando campos obrigatórios vazios após a normalização. Quantidade continua estritamente maior que zero. O vínculo com motivo preserva o texto como snapshot. A checagem de referências em memória usa a operação protegida pelo lock do repositório; no PostgreSQL, a FK e o bloqueio `FOR UPDATE` permanecem como salvaguardas transacionais.

Foram adicionados testes para esses casos, mas não foram executados nesta etapa. A proteção de concorrência do repositório em memória não equivale à transação PostgreSQL; o modo memória permanece destinado a testes/desenvolvimento.


## Inventário de exposição dos routers — revisão complementar

Revisão estática dos decorators dos 15 routers de negócio e do router de identidade. Nesta revisão, nenhum decorator de rota de negócio declara `Depends(get_current_principal)`, `require_capability_dependency` ou outra dependência de autorização.

| Módulo | Operações encontradas | Observação de risco |
|---|---|---|
| Usuários | GET lista/detalhe, POST, PUT, DELETE | **Crítico:** POST/PUT aceitam perfil e status; sem autorização, podem criar ou alterar contas privilegiadas. |
| Financeiro | GET, POST, PUT, DELETE | **Crítico:** leitura e alteração de dados financeiros sem identidade exigida. |
| Moradores | GET, POST, PUT, DELETE, POST importar | **Crítico:** dados pessoais e importação sem autorização. |
| Empregados | GET, POST, PUT, DELETE | **Crítico:** dados funcionais pessoais sem autorização. |
| Documentos | GET lista/detalhe, POST, PUT, DELETE | **Crítico:** documentos e conteúdo armazenado sem autorização. |
| Contas Bancárias | GET, POST, PUT, DELETE | **Alto:** dados e saldos informados sem autorização. |
| Plano de Contas | GET, POST, PUT, DELETE | **Alto:** estrutura contábil alterável sem autorização. |
| Estoque | GET, POST, PUT, DELETE | **Alto:** cadastro e inventário sem autorização; regras de imutabilidade devem continuar no serviço. |
| Acertos de Estoque | GET, POST, DELETE | **Alto:** movimentações consultáveis/criáveis sem autorização; exclusão deve continuar bloqueada pela regra de domínio. |
| Fornecedores | GET, POST, PUT, DELETE | **Alto:** dados cadastrais e comerciais sem autorização. |
| Condomínio | GET, PUT | **Alto:** dados institucionais sem autorização. |
| Conselheiros | GET, POST, PUT, DELETE | **Alto:** cadastro pessoal e institucional sem autorização. |
| Formas Monetárias | GET, POST, PUT, DELETE | **Médio:** configuração financeira sem autorização. |
| Categorias | GET, POST, DELETE | **Médio:** configuração sem autorização. |
| Motivos de Acerto | GET, POST, DELETE | **Médio:** configuração sem autorização. |
| Autenticação | GET /auth/me | Protegido por validação do ID token Google e vínculo ao usuário interno ativo. |
| Saúde | GET /health | Público intencionalmente; informa somente serviço, versão e modo de armazenamento, não consulta dados. |

### Conclusão técnica

- O inventário confirma que o endpoint `/api/v1/auth/me` é protegido, mas os routers de negócio não estão protegidos por autenticação/autorização.
- A rota de Usuários exige atenção especial: o schema permite `perfil=Admin` e `status=Ativo`; não há controle de quem pode atribuir esses valores enquanto o router estiver aberto.
- A existência do catálogo `ROLE_CAPABILITIES` não protege nenhuma rota por si só.
- O agregador interno do Dashboard continua sem endpoint HTTP, portanto não amplia a superfície de exposição.
- Não aplicar uma proteção global improvisada: a integração deve mapear cada método HTTP para uma capacidade explícita, incluir testes 401/403/permitido por rota e tratar primeiro o provisionamento seguro do primeiro administrador.
- Até essa etapa, a API sombra não deve ser publicada para acesso público nem receber dados reais.

### Ordem de implementação recomendada

1. Definir provisionamento seguro do primeiro Admin e impedir autoatribuição de perfil/status.
2. Aprovar a matriz de permissões por módulo e operação.
3. Aplicar dependências de autenticação e capacidade a cada rota, começando por Usuários e módulos sensíveis.
4. Criar testes de integração 401, 403 e acesso permitido para cada grupo de rotas.
5. Só então expor os endpoints de Dashboard e relatórios.


## Achado prioritário — provisionamento do primeiro Admin

A revisão do schema, serviço, router e testes de Usuários confirmou que:

- `UsuarioInput` permite `perfil=Admin` e `status=Ativo`.
- `POST /api/v1/usuarios` e `PUT /api/v1/usuarios/{item_id}` não exigem identidade autenticada nem capacidade administrativa.
- O teste `test_create_and_get_profile_by_email` cria um Admin por chamada HTTP sem Bearer token. Esse teste documenta o comportamento atual, não um comportamento seguro.
- O backend padrão usa armazenamento em memória; portanto, criar um primeiro Admin nesse modo não é provisionamento persistente.

**Bloqueio:** não implementar bootstrap via endpoint HTTP, não confiar em primeiro login e não permitir que o payload do cliente escolha o perfil. O desenho recomendado de provisionamento fora da API está em `docs/provisionamento-primeiro-admin.md`. A implementação depende de PostgreSQL local de sombra, transação atômica, e-mail explicitamente autorizado pelo responsável e proteção das rotas de Usuários.


## Atualização de estado — cobertura HTTP e negação por padrão (27/11/2026)

Esta seção prevalece sobre os registros históricos anteriores que descrevem os routers como desprotegidos. As seções antigas registram o estado em que foram produzidas; não devem ser lidas como retrato atual.

### Evidência estática atual

- `backend/app/modules/estoque/router.py` (e os demais routers de negócio) declara `Depends(require_capability_dependency(...))` por operação.
- `backend/app/core/authorization.py` cria a dependência que obtém `get_current_principal`, valida a capacidade e retorna 403 quando ela não é concedida.
- `backend/app/core/authentication.py` valida o Bearer ID token Google no servidor e resolve o e-mail verificado para um cadastro Bravo único e ativo.
- `backend/tests/test_route_authentication_coverage.py` contém verificações automatizadas de cobertura de identidade e de capacidade para as rotas de negócio, com exceção explícita de `/api/v1/auth/me` para a segunda verificação.
- `ROLE_CAPABILITIES` permanece vazio para os dois perfis. Não há concessão funcional implícita a Admin nem a Operador.

### Limites da evidência

A inspeção acima é leitura de código e de testes; não equivale a teste de penetração, validação de token real no ambiente, nem prova de que uma identidade PostgreSQL de runtime esteja corretamente configurada. O workflow de CI ainda está executando os testes de backend no PostgreSQL descartável; até sua conclusão, não declarar a suíte aprovada.

### Decisão de segurança preservada

Não preencher a matriz de perfis por inferência. Até aprovação explícita, as rotas continuam negando todas as capacidades de negócio, mesmo para Admin autenticado e ativo. Não habilitar dados reais, banco remoto, cutover ou publicação pública com base apenas na presença dos decorators.


### Ponto de decisão — chave persistente da identidade Google (27/11/2026)

A implementação atual valida o ID token Google e exige `sub`, e-mail e `email_verified=true`. A resolução do cadastro Bravo é feita por comparação do e-mail normalizado, exigindo exatamente um cadastro com status `Ativo`. O `sub` validado é colocado em `AuthenticatedPrincipal` e usado como ator técnico em contexto/auditoria, mas os schemas de cadastro e atualização cadastral de usuários não expõem nem persistem esse identificador.

**Consequência:** hoje, o e-mail verificado é a chave de associação entre a identidade Google e o cadastro interno. Não há evidência nesta revisão de vínculo durável por `sub`. Uma mudança futura de e-mail na conta Google exigiria um processo controlado de reconciliação com o cadastro Bravo; não se deve associar automaticamente uma identidade nova apenas porque ela informa um endereço semelhante.

**Decisão necessária antes de evoluir o modelo:** manter e-mail verificado como chave oficial, com processo administrativo de troca/reconciliação, ou introduzir um campo persistente e único para o `sub` do Google. Não alterar schema, migrations ou registros até essa decisão ser aprovada. O fluxo continua sem senha local e sem permitir que o navegador escolha perfil/status.
