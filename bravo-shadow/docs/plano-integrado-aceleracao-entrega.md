# Plano integrado de aceleração — Bravo Shadow

Data da revisão: 2026-11-27  
Branch-base revisada: `bravo-shadow`  
HEAD revisado: `94d1de6bcbb4bf7d9e02bd81486002be7a933cb6`

## Decisão de execução

Parar de abrir novas frentes de verificações estáticas isoladas. A prioridade passa a ser fechar um fluxo integrado, automatizado e repetível, mantendo o Bravo original e qualquer banco de produção fora do caminho.

O objetivo da próxima entrega é demonstrar, em um único pipeline, que a imagem sobe, as migrations criam o schema do zero, a API inicia, a autenticação e autorização bloqueiam acessos indevidos, os módulos habilitados persistem dados sintéticos e a reconciliação confirma o resultado.

## Diagnóstico confirmado no repositório

| Área | O que existe | O que ainda impede considerar pronto |
|---|---|---|
| Frontend | Aplicação estática unificada, tema Bravo, navegação responsiva e telas de vários módulos | Nem todos os módulos têm fluxo completo conectado; módulos não migrados ainda exibem estrutura inicial |
| API | FastAPI, rotas para os módulos e cliente HTTP comum | É necessário comprovar os fluxos integrados com o backend real e persistente |
| Persistência | Driver Psycopg, adaptadores PostgreSQL e seleção explícita por configuração | O modo PostgreSQL conecta vários adaptadores; exige validar schema, permissões, RLS e CRUD em conjunto |
| Banco | Seis migrations versionadas; CI agora aplica as seis migrations em PostgreSQL descartável e executa auditoria de catálogo após a aplicação | A execução ainda precisa ser observada em um workflow concluído; homologação local do desenvolvedor não foi realizada |
| Autenticação | Validação server-side de identidade Google e módulo cliente | Bootstrap do frontend fica desligado sem API HTTPS Shadow validada e origem OAuth/CORS exatas |
| CI | GitHub Actions constrói o Docker, faz smoke test HTTP, aplica migrations em PostgreSQL descartável, audita o catálogo e executa pytest | É necessário acompanhar o resultado do workflow; execução em CI não comprova OAuth, frontend completo nem todos os CRUDs em produção |
| Preview | GitHub Pages valida/publica arquivos estáticos | Não hospeda FastAPI, banco nem autenticação; não pode ser apresentado como sistema operacional completo |
| Implantação | Dockerfile e blueprint Render preparados | Nenhum ambiente hospedado foi validado; não publicar nem conectar serviços remotos sem revisão e autorização separadas |

## Pacote único de trabalho — ordem obrigatória

### 1. Pipeline integrado de banco e aplicação
- [x] Construir a imagem do Bravo Shadow no job de container.
- [x] Subir PostgreSQL descartável e aguardar healthcheck no job de backend.
- [x] Aplicar, em ordem, as seis migrations da branch, desde banco vazio.
- [x] Executar a auditoria de catálogo depois da aplicação.
- [x] Executar inspeção SQL de privilégios/RLS somente leitura.
- [ ] Observar workflow concluído e corrigir eventuais falhas; a configuração do pipeline não equivale a execução bem-sucedida.
- [ ] Confirmar descarte do banco ao fim do job pelo encerramento do runner efêmero.

### 2. Teste ponta a ponta da API
- Iniciar a API com configuração exclusiva de teste.
- Exercitar healthcheck e OpenAPI.
- Executar CRUD integrado para cada módulo que esteja habilitado no adaptador PostgreSQL.
- Testar relações entre Plano de Contas e Financeiro, Estoque e Acertos, além das restrições de exclusão.
- Testar transações, rollback, concorrência por versão, auditoria e persistência após reiniciar a API.
- Usar exclusivamente registros sintéticos, com identificadores de teste e limpeza controlada.

### 3. Segurança e identidade
- Definir a role mínima da API e policies RLS explícitas; não usar superusuário nem BYPASSRLS como solução.
- Verificar que anon e authenticated não recebem acesso indevido.
- Validar token Google, audience, issuer, expiração, e-mail verificado, usuário cadastrado/ativo e capacidades.
- Configurar CORS e origens OAuth exatas apenas no ambiente Shadow.
- Manter o frontend sem chamadas de API enquanto a configuração HTTPS não estiver validada.

### 4. Integração real do frontend
- Ligar cada tela a rotas já existentes e a capacidades do backend.
- Priorizar o fluxo comum: autenticar, consultar, cadastrar, editar, excluir quando permitido, atualizar lista e apresentar erros.
- Onde não houver contrato/API completo, manter a tela explicitamente indisponível; não simular persistência.
- Fazer uma única rodada de revisão de responsividade, acessibilidade, mensagens e estados de carregamento após a integração.

### 5. Homologação e liberação
- Gerar relatório único com commit, versão das migrations, resultado de cada módulo e evidências do pipeline.
- Corrigir em lote as falhas encontradas e repetir o pipeline integrado.
- Só depois preparar um ambiente Shadow separado para avaliação funcional.
- Importação real e promoção ao Bravo original continuam bloqueadas até aprovação explícita, backup, reconciliação e plano de reversão.

## Critérios objetivos de conclusão

- [ ] Build Docker e smoke test passam.
- [ ] Seis migrations aplicam do zero em PostgreSQL descartável.
- [ ] Auditoria do catálogo passa após as migrations.
- [ ] CRUD integrado e persistência passam para os módulos declarados como habilitados.
- [ ] Relações, transações, rollback e auditoria passam.
- [ ] RLS, policies, grants e capacidades passam sem privilégios amplos.
- [ ] Login Google é validado no ambiente Shadow, sem segredos no frontend.
- [ ] Telas conectadas refletem dados da API; telas pendentes ficam identificadas.
- [ ] Relatório único de homologação é publicado.
- [ ] Nenhuma conexão ou escrita no Bravo original ocorreu.

## Regra de aceleração

Acelerar significa executar verificações complementares no mesmo pipeline e corrigir grupos de problemas por causa raiz. Não significa pular testes de integração, aprovar SQL não aplicado, inventar dados persistidos ou publicar um serviço incompleto.

### Correção adicional do pipeline Docker

O smoke test do contêiner agora fornece valores sintéticos explícitos para `BRAVO_STORAGE_BACKEND=postgres`, `BRAVO_DATABASE_URL` e `GOOGLE_CLIENT_ID`, atendendo ao `CMD` fail-closed do Dockerfile. A URL é deliberadamente fictícia e não é usada pelo healthcheck; o smoke test verifica apenas a inicialização HTTP e a interface, sem realizar operações de negócio nem conectar a um banco remoto.

## Limites desta revisão

Esta revisão dos arquivos foi estática. O workflow foi atualizado para aplicar as seis migrations no PostgreSQL descartável do GitHub Actions antes da auditoria e também para disparar em pull requests que alterem migrations ou scripts de homologação. Não executei Docker, PostgreSQL, migrations, pytest, OAuth ou deploy nesta sessão. Os itens marcados como concluídos descrevem etapas configuradas no workflow, não resultados de uma execução já observada.


### Financeiro — integração de auditoria atômica

As mutações do Financeiro foram implementadas no repositório PostgreSQL com `add_audited`, `replace_if_version_audited` e `delete_audited`. O serviço cria eventos vinculados ao principal interno ativo e ao request ID; as rotas HTTP encaminham esse contexto. A mutação e o evento append-only usam a mesma conexão/unidade de trabalho, portanto falha no INSERT de auditoria reverte a alteração de negócio. A edição mantém compare-and-swap e ETag/If-Match; o vínculo ao Plano de Contas continua protegido pela FK. O sink foi injetado no composition root. A interface segue somente leitura até homologação do fluxo completo.

### Correções encontradas durante o CI

A execução automatizada identificou dois problemas de coleta Python independentes do Financeiro: anotação `list[...]` avaliada contra um método homônimo no serviço de Documentos e um trecho de teste de integridade com string não terminada. Ambos foram corrigidos na branch Shadow. O smoke test Docker passou na execução observada; a execução de backend precisa ser repetida após as correções para confirmar a coleta e o conjunto completo. Nenhum dado real foi usado e nenhuma conexão de produção foi realizada.


### Formas Monetárias e Contas Bancárias — auditoria transacional integrada

Os dois módulos passaram a receber o sink de auditoria no composition root e a encaminhar identidade interna ativa e request ID pelas rotas. Os serviços emitem eventos específicos para criação, edição e exclusão; os repositórios PostgreSQL executam cada mutação e o INSERT em `audit_events` na mesma unidade de trabalho, sem commit intermediário. Se a mutação ou o INSERT de auditoria falhar, a transação é revertida. O modo de memória segue disponível para testes isolados. Foram incluídos testes do contrato de serviço para as três operações e do bloqueio quando não há ator autenticado. A integração de código está concluída; ainda depende de CI e homologação PostgreSQL descartável antes de ser considerada validada. Esses dois cadastros não têm controle de concorrência por versão exposto no contrato HTTP nesta etapa.


### Usuários — auditoria das alterações cadastrais

As rotas de criação e atualização cadastral agora encaminham ator interno e request ID. No modo PostgreSQL, ambas exigem perfil Admin ativo e métodos dedicados do repositório; criação de usuário comum (Operador/Ativo) e atualização apenas de nome/loja/cargo são gravadas junto com o evento de auditoria na mesma transação. O repositório não aceita perfil/status no payload cadastral, não permite exclusão física e preserva o fluxo administrativo privilegiado separado. Falta validar os novos contratos no CI e no PostgreSQL descartável; não há autorização de importação ou mudança de produção implícita.


### Moradores, Fornecedores e Empregados — bloqueio preventivo de gravações

As rotas passaram a encaminhar identidade interna e request ID aos serviços, e o composition root injeta o sink de auditoria. Como os repositórios PostgreSQL desses três módulos ainda não possuem operações de escrita auditadas no mesmo contrato transacional, as mutações no modo persistente agora falham fechadas com HTTP 503, em vez de gravar sem trilha de auditoria. Leituras continuam disponíveis; o modo memória isolado mantém seu comportamento de desenvolvimento. A implementação transacional de escrita e os testes integrados continuam pendentes. Nenhum dado real foi importado.

### Moradores, Fornecedores e Empregados — auditoria transacional

As mutações individuais de moradores, fornecedores e empregados passaram a usar contratos `add_audited`, `replace_audited` e `delete_audited` nos repositórios PostgreSQL. Cada operação executa a escrita de negócio e o append do evento de auditoria na mesma unidade de trabalho/conexão; falha no append provoca rollback. Os serviços exigem principal interno ativo quando o sink persistente está configurado e falham de forma fechada se o contrato auditado não estiver disponível. A atualização e a exclusão verificam a quantidade de linhas afetadas dentro da transação, sem depender de uma leitura prévia separada.

A importação em lote de moradores permanece bloqueada no modo PostgreSQL até existir um contrato transacional próprio para o lote inteiro. Os testes de integração com PostgreSQL descartável e a execução CI deste commit ainda precisam ser observados; a implementação não equivale a homologação aprovada.
