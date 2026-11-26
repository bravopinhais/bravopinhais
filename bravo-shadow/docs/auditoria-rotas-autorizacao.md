# Auditoria de rotas e autorização funcional — Bravo Shadow

## Resultado executivo

Revisão estática dos 15 arquivos `router.py` e de `backend/app/main.py`, na branch `bravo-shadow`.

**Achado crítico:** as rotas de negócio revisadas não declaram dependências de autenticação/autorização (não há `Depends` de segurança nos handlers). Cada router obtém diretamente o serviço em `request.app.state.services`. Assim, a existência de cadastro de usuários e de uma role técnica PostgreSQL não protege, por si só, os endpoints HTTP.

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
| Acertos de Estoque | `/api/v1/acertos-estoque` | GET lista; POST registra movimento; DELETE rota legada, bloqueada no serviço persistente |
| Documentos | `/api/v1/documentos` | GET lista; GET por ID; POST cria; PUT altera; DELETE exclui |
| Usuários | `/api/v1/usuarios` | GET lista; GET por ID; POST cria; PUT altera; DELETE exclui |

## Situação atual da segurança HTTP

- Os handlers não declaram dependências de autenticação/autorização.
- Os routers recuperam os serviços diretamente de `request.app.state.services`.
- O cadastro `usuarios` guarda e-mail, nome, loja, cargo, perfil e status; não valida token Google.
- Os valores de perfil aceitos atualmente são `Admin` e `Operador`, mas não há matriz funcional implementada que associe esses valores a permissões.
- O campo `status` do cadastro não bloqueia por si só o acesso HTTP.
- O vínculo entre e-mail autenticado e registro de usuário ainda precisa ser validado pelo backend.
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
| Acertos de Estoque — DELETE legado | `/api/v1/acertos-estoque/{item_id}` | **Sem capacidade de exclusão**; preservar bloqueio/409 no serviço persistente e avaliar retirada da rota legada |
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


## Proteção inicial do módulo de usuários — implementada na branch sombra

As rotas de gestão de usuários passaram a exigir as capacidades centrais
`usuarios:read`, `usuarios:create`, `usuarios:update` e
`usuarios:delete`, respectivamente. Como a política atual concede essas
capacidades somente ao perfil Admin autenticado e ativo, o Operador recebe
403 até aprovação de uma matriz diferente.

Também foram acrescentadas salvaguardas contra autoelevação:
- usuário autenticado não pode alterar o próprio e-mail, perfil ou status;
- usuário autenticado não pode excluir o próprio cadastro;
- alteração de outros cadastros continua sujeita à capacidade `usuarios:update`;
- criação de novo Admin exige a capacidade `usuarios:create`, hoje restrita a Admin.

Foram adicionados testes HTTP em
`backend/tests/test_usuarios_authorization.py` para ausência de identidade,
negação do Operador, tentativa de alterar os próprios dados protegidos,
exclusão do próprio cadastro e operações administrativas sobre outro usuário.

**Limite:** os testes foram escritos, mas não executados neste ambiente. A
proteção foi aplicada apenas ao router de usuários; os outros 14 módulos
continuam sem dependências de autorização e não devem ser expostos como API
pública. Esta implementação permanece na branch `bravo-shadow`.


## Proteção do módulo Financeiro — implementada na branch sombra

As quatro operações do router `/api/v1/financeiro` agora exigem:
- GET/listagem: `financeiro:read`;
- POST/criação: `financeiro:create`;
- PUT/alteração: `financeiro:update`;
- DELETE/exclusão: `financeiro:delete`.

A dependência central valida o Bearer token Google, resolve o cadastro Bravo
ativo e consulta a capacidade do perfil interno. O perfil Operador continua
sem capacidades concedidas até aprovação formal da matriz.

O controle de concorrência existente foi preservado: PUT continua exigindo
ETag forte em `If-Match` e mantém os retornos de versão/ conflito do serviço.

Foram adicionados testes HTTP em
`backend/tests/test_financeiro_authorization.py` cobrindo ausência de
identidade, bloqueio do Operador e operações autorizadas de leitura, criação,
alteração e exclusão.

**Limite atualizado:** os módulos Usuários e Financeiro estão protegidos na
branch sombra. Os outros 13 módulos de negócio ainda não estão protegidos.
Os testes foram escritos, mas não executados neste ambiente. Não expor a API
sombra publicamente enquanto os módulos restantes e a configuração OAuth
não forem validados.
