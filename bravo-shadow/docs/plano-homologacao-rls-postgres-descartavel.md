# Plano de homologação de RLS e privilégios — PostgreSQL descartável

**Status:** plano de execução; não executado.  
**Escopo:** preparar a prova de privilégios efetivos do ledger de revisão do Bravo Shadow.  
**Ambiente permitido:** PostgreSQL local descartável ou serviço efêmero de CI.  
**Fora do escopo:** Supabase hospedado, banco compartilhado, produção, dados legados e ativação funcional da revisão.

## 1. Resultado da revisão do estado atual

A cobertura existente comprova integridade e concorrência do adaptador, mas ainda não comprova o isolamento por roles:

- A fixture `backend/tests/test_migration_review_postgres_integration.py` exige `BRAVO_SHADOW_ALLOW_DESTRUCTIVE_TEST_DATABASE=1`, nome exato `bravo_shadow_test` e host local (`localhost`, `127.0.0.1` ou `::1`).
- A fixture cria `anon`, `authenticated` e `service_role` como `NOLOGIN` quando ausentes, remove `bravo_shadow` com `CASCADE` e aplica o SQL de rascunho. A conexão usada pelos testes é a conexão configurada para a fixture.
- Os testes atuais cobrem concorrência, idempotência, unicidade e rollback. Eles não abrem sessões independentes com roles runtime/writer/reader.
- O SQL de rascunho habilita RLS e revoga privilégios de roles padrão, mas não cria roles privadas, grants ou policies. Portanto, não há ainda uma matriz de acesso operacional a validar.
- O script `verificar-privilegios-rls-somente-leitura.sql` consulta catálogos em transação read-only. Sua execução anterior no CI ocorreu em PostgreSQL 16 vazio, antes de a fixture criar o schema; isso validou a execução das consultas, não o desenho de RLS do Bravo.

## 2. Barreiras obrigatórias antes de qualquer execução destrutiva

A execução de integração com a fixture atual só pode ocorrer quando todas as condições forem verdadeiras:

1. Instância PostgreSQL descartável recém-criada, sem dados úteis ou compartilhados.
2. Banco chamado exatamente `bravo_shadow_test`.
3. Host local/loopback; nunca hostname remoto.
4. Variável `BRAVO_SHADOW_ALLOW_DESTRUCTIVE_TEST_DATABASE=1` definida conscientemente apenas para essa execução.
5. URL de conexão fornecida diretamente ao processo de teste, sem gravá-la em arquivos versionados, logs, artefatos ou documentação.
6. Nenhuma URL, senha, token ou segredo de produção/Supabase hospedado presente no ambiente.
7. Confirmação de que o banco será descartado ao final e que a fixture pode remover o schema `bravo_shadow` com `CASCADE`.

A transação `ROLLBACK` não substitui o isolamento físico/lógico do banco descartável. Não executar se qualquer pré-condição for incerta.

## 3. Fases de homologação

### Fase A — inspeção somente leitura

Pode ser feita sem alterar o banco, desde que a conexão já esteja apontada para a instância descartável correta.

- Registrar `current_database()`, `session_user`, `current_user` e versão do PostgreSQL.
- Executar `docs/verificar-privilegios-rls-somente-leitura.sql`.
- Guardar saída de atributos de roles, memberships efetivas, ownership, flags RLS, policies, privilégios de tabelas/schema/sequences/funções e ACL.
- Repetir a inspeção depois da instalação do schema de teste, para que os resultados incluam os objetos reais da fixture.

**Critério:** qualquer identidade runtime com `SUPERUSER`, `BYPASSRLS`, ownership ou membership privilegiada bloqueia a homologação.

### Fase B — preparação de roles e grants

Esta fase altera o banco e **não está autorizada por este plano**. Exige aprovação explícita do desenho de roles, nomes, privilégios e SQL antes de ser preparada ou executada.

O desenho proposto separa:
- identidade de migration/owner, usada somente em preparação controlada;
- identidade privada de runtime, sem ownership nem atributos administrativos;
- writer e reader de auditoria, caso permaneçam necessários, com escopos independentes;
- roles padrão `PUBLIC`, `anon`, `authenticated` e `service_role`, sem acesso ao schema privado.

Não reutilizar uma credencial privilegiada para simular todas as identidades. Não conceder membership ampla para facilitar os testes. Não usar `service_role` como atalho.

### Fase C — sessões independentes e matriz de operações

Depois da aprovação da Fase B, abrir conexões independentes autenticadas como cada role de teste. `SET ROLE` pode complementar, mas não substituir, os testes com credenciais/sessões próprias.

| Identidade | SELECT | INSERT events | INSERT batches/decisions | UPDATE/DELETE/TRUNCATE | DDL |
|---|---|---|---|---|---|
| runtime de revisão | somente tabelas aprovadas | somente se concedido no desenho final | negado no desenho atual | negado | negado |
| writer de auditoria | negado, salvo aprovação explícita | permitido apenas no destino aprovado | negado | negado | negado |
| reader de auditoria | somente escopo aprovado | negado | negado | negado | negado |
| anon | negado | negado | negado | negado | negado |
| authenticated | negado | negado | negado | negado | negado |
| service_role | negado no schema privado | negado | negado | negado | negado |
| migration/owner | conforme procedimento controlado | fora do runtime | somente preparação | fora do runtime | somente ciclo controlado |

A matriz é uma expectativa de desenho, não uma autorização para conceder acesso. A matriz definitiva deve ser aprovada antes da Fase B.

Para cada sessão, testar tanto operações permitidas quanto negadas: SELECT, INSERT, UPDATE, DELETE, TRUNCATE e DDL; verificar também `SET ROLE`, memberships transitivas, ownership, privilégios herdados, `BYPASSRLS` e efeito de `FORCE ROW LEVEL SECURITY`. Usar apenas registros sintéticos e transações descartáveis.

### Fase D — regressão funcional e de isolamento

- Preservar os testes existentes de concorrência, versão otimista, idempotência, unicidade e rollback.
- Confirmar que o runtime não consegue inicializar lotes ou fotografias de decisões se essa operação exigir credencial de migration.
- Separar o adaptador de preparação do adaptador runtime antes de conectar o serviço à API.
- Confirmar que falha de privilégio não aciona fallback para memória.
- Confirmar que a autorização da aplicação continua negando por padrão e que o ator deriva do principal Google validado.
- Confirmar que nenhuma rota pública ou capacidade foi ativada como efeito colateral da homologação SQL.

## 4. Evidências exigidas para aceite

Registrar, sem segredos nem dados pessoais:

- commit exato do código e hash do SQL testado;
- versão do PostgreSQL e nome do banco descartável;
- saída das consultas de catálogo antes e depois do schema;
- identidade efetiva de cada conexão de teste;
- resultado permitido/negado de cada operação por role;
- memberships diretas e transitivas, ownership, flags RLS e privilégios herdados;
- resultados dos testes funcionais e de concorrência;
- confirmação de descarte do banco de teste.

O aceite exige revisão independente da matriz completa. Uma execução bem-sucedida do script somente leitura ou dos testes atuais do adaptador não substitui essa evidência.

## 5. Bloqueios que permanecem

Até aprovação explícita e homologação isolada:

- não criar roles privadas, memberships, grants ou policies;
- não aplicar migrations nem executar o rascunho fora da fixture efêmera existente;
- não conectar Supabase hospedado, banco compartilhado ou produção;
- não importar dados reais;
- não montar rotas de revisão nem ativar capacidades;
- não habilitar dual-write, cutover ou qualquer fluxo de migração operacional.

**Conclusão:** o repositório possui uma base útil de testes de integridade do ledger e uma inspeção de catálogo somente leitura. A prova de RLS e privilégios efetivos continua pendente; este documento organiza a próxima homologação sem antecipar alterações de segurança no banco.

## 6. Decisão de arquitetura pendente: runtime de revisão x auditoria

A documentação existente descreve dois escopos que não devem ser confundidos:

- **Runtime de revisão:** precisa consultar lotes/decisões/eventos e, conforme o desenho atual, inserir eventos de revisão. O serviço de revisão usa um adaptador próprio e permanece desativado.
- **Auditoria técnica geral:** o backend possui um `PostgresAuditSink` para eventos de auditoria da aplicação, com escrita transacional. Esse fluxo não é automaticamente o mesmo que o ledger de revisão humana.

Antes da Fase B, a matriz deve declarar explicitamente se haverá:
1. uma role privada de runtime para o ledger de revisão, com SELECT no escopo aprovado e INSERT somente em `migration_review_events`; e
2. uma role distinta para o sink de auditoria geral, com INSERT somente na tabela de auditoria técnica; ou
3. um desenho consolidado, acompanhado de justificativa de menor privilégio e testes que provem que um fluxo não consegue ler ou alterar os dados do outro.

Não criar simultaneamente roles `runtime`, `writer` e `reader` apenas porque aparecem em documentos diferentes. Primeiro mapear cada adaptador real, tabela e operação. Uma role de leitura separada só é necessária se existir consumidor de leitura independente; não presumir sua necessidade.

**Recomendação para revisão, ainda não aprovada nem implementada:** manter owner/migrator separado de todas as credenciais de processo; manter o runtime de revisão com SELECT nas tabelas do ledger e INSERT apenas em events; manter a auditoria técnica geral com credencial de escrita isolada, caso o sink seja habilitado em PostgreSQL. A role e os grants finais dependem da confirmação dos adaptadores e de revisão explícita.

Esta decisão é um bloqueio de desenho para a Fase B. Nenhuma role, membership, policy ou grant é criada por esta documentação.

## 7. Mapa dos adaptadores PostgreSQL observados no código

A inspeção do composition root `backend/app/core/storage.py` e dos adaptadores `backend/app/core/postgres_*.py` confirmou o seguinte escopo de persistência:

| Adaptador | Tabelas acessadas |
|---|---|
| `PostgresFormasMonetariasRepository` | `formas_monetarias` |
| `PostgresPlanoContasRepository` | `plano_contas` |
| `PostgresFinanceiroRepository` | `financeiro` |
| `PostgresEstoqueRepository` | `estoque` |
| `PostgresAcertosEstoqueRepository` | `acertos_estoque` |
| `PostgresCategoriasRepository` | `categorias` |
| `PostgresMotivosAcertoRepository` | `motivos_acerto` |
| `PostgresDocumentosRepository` | `documentos` |
| `PostgresMoradoresRepository` | `moradores` |
| `PostgresFornecedoresRepository` | `fornecedores` |
| `PostgresEmpregadosRepository` | `empregados` |
| `PostgresContasBancariasRepository` | `contas_bancarias` |
| `PostgresCondominioRepository` | `condominio` |
| `PostgresConselheirosRepository` | `conselheiros` |
| `PostgresUsuariosRepository` | `usuarios` |
| `PostgresAuditSink` | `audit_events` |

Todas as tabelas acima pertencem ao schema `bravo_shadow`. A lista descreve o código encontrado, não prova que todas as tabelas estejam implantadas em um banco.

### Achado importante: a fábrica de conexão é compartilhada

No modo `postgres`, `build_storage_services` recebe uma única `connection_factory` e a injeta nos repositórios de domínio, no repositório de usuários e no `PostgresAuditSink`. Portanto, no estado atual, o código não separa credenciais PostgreSQL para domínio, auditoria geral e revisão humana. A proposta de roles isoladas não pode ser considerada implementada apenas por existir um sink dedicado: ele recebe a mesma fábrica.

Antes de conceder privilégios, será necessário decidir se o backend usará uma única role técnica com grants mínimos agregados ou se o composition root será alterado para aceitar fábricas distintas por fronteira de confiança. A segunda opção reduz o escopo de cada credencial, mas exige rever operações transacionais que hoje compartilham conexão — especialmente a desativação de usuário, que grava alteração cadastral e evento de auditoria na mesma transação via `append_in_transaction`.

### Consequências para a matriz

- A role que atende os repositórios de domínio precisa do conjunto de operações realmente utilizado pelos 15 adaptadores, não apenas do ledger de revisão.
- O `PostgresAuditSink` oferece somente INSERT em `audit_events`; não implementa leitura, atualização ou exclusão.
- A desativação de usuário executa LOCK/SELECT/UPDATE em `usuarios` e insere o evento de auditoria na mesma conexão/transação. Separar credenciais nesse fluxo exigiria um desenho transacional explícito; não basta trocar a fábrica do sink.
- `PostgresUsuariosRepository.delete` bloqueia exclusão física na camada Python (HTTP 410), mas a role SQL ainda precisaria ser testada sem DELETE se a política de segurança exigir essa barreira no banco.
- `PostgresAcertosEstoqueRepository.replace` e `delete` bloqueiam mutações na camada Python; os privilégios SQL também precisam negar UPDATE/DELETE diretamente.

**Decisão recomendada para a próxima revisão:** não criar ainda roles writer/reader independentes para auditoria. Primeiro fechar a fronteira de conexão: (a) uma role única de API, com grants mínimos agregados e RLS apropriada, ou (b) múltiplas connection factories com transação coordenada/atômica para operações que escrevem negócio e auditoria. A opção (b) não deve ser implementada sem projeto transacional específico. A role do ledger de revisão permanece separada e inativa até existir adaptador efetivamente conectado.

Nenhuma fábrica de conexão foi alterada e nenhuma role ou permissão foi criada nesta etapa.

## 8. Matriz CRUD observada nos adaptadores atuais

Esta matriz foi extraída dos métodos SQL dos repositórios PostgreSQL. Ela representa o que o código tenta executar hoje; não representa grants concedidos nem autorização de negócio. `SELECT` inclui listagem, busca, verificação de existência e consultas de referência.

| Tabela | SELECT | INSERT | UPDATE | DELETE | Observação |
|---|:---:|:---:|:---:|:---:|---|
| `plano_contas` | Sim | Sim | Sim | Sim | Atualização também usa controle otimista de versão. |
| `financeiro` | Sim | Sim | Sim | Sim | Consulta referências do plano de contas. |
| `formas_monetarias` | Sim | Sim | Sim | Sim | CRUD convencional. |
| `moradores` | Sim | Sim | Sim | Sim | CRUD convencional. |
| `fornecedores` | Sim | Sim | Sim | Sim | CRUD convencional. |
| `empregados` | Sim | Sim | Sim | Sim | CRUD convencional. |
| `contas_bancarias` | Sim | Sim | Sim | Sim | CRUD convencional. |
| `condominio` | Sim | Sim | Sim | Não | O adaptador não oferece exclusão. |
| `conselheiros` | Sim | Sim | Sim | Sim | CRUD convencional. |
| `categorias` | Sim | Sim | Sim | Sim | Exclusão usa helper compartilhado com verificação de referências. |
| `motivos_acerto` | Sim | Sim | Sim | Sim | Exclusão usa helper compartilhado com verificação de referências. |
| `documentos` | Sim | Sim | Sim | Sim | Exclusão usa helper compartilhado; há verificação de vínculo com categoria. |
| `estoque` | Sim | Sim | Sim | Sim | Edição bloqueia alteração direta do saldo após movimentação; exclusão verifica referências. |
| `acertos_estoque` | Sim | Sim | Não | Não | Histórico imutável: edição/exclusão são recusadas pela camada Python. |
| `usuarios` | Sim | Sim | Sim | Não | Exclusão física retorna HTTP 410; desativação e alteração administrativa usam UPDATE e lock de tabela. |
| `audit_events` | Não | Sim | Não | Não | Sink oferece somente INSERT; não implementa leitura. |

### Leitura de segurança da matriz

1. **A role única de API, se escolhida, não pode receber `DELETE` irrestrito em todas as tabelas.** `condominio`, `acertos_estoque`, `usuarios` e `audit_events` não necessitam de DELETE conforme o código atual.
2. **`acertos_estoque` requer INSERT e SELECT, sem UPDATE/DELETE.** O movimento é histórico; a alteração de saldo ocorre no fluxo transacional que atualiza `estoque` e insere o acerto.
3. **`audit_events` requer INSERT para o sink.** O sink não precisa de SELECT/UPDATE/DELETE. A leitura administrativa de auditoria, se vier a existir, deverá ser desenhada como consumidor separado e aprovado.
4. **`usuarios` requer SELECT/INSERT/UPDATE e capacidade de lock compatível com as operações administrativas atuais.** A permissão SQL de DELETE não é necessária. O lock `SHARE ROW EXCLUSIVE` deve ser incluído no teste de compatibilidade de privilégios; não presumir que grants de tabela o resolvam.
5. **As demais tabelas apresentam CRUD no código.** Isso não significa que todo usuário do sistema possa executar todas as operações: a camada de autorização HTTP continua sendo uma fronteira independente e atualmente permanece fechada por padrão.
6. **Privilégios de schema, sequences, funções, ownership, memberships e RLS ainda precisam ser verificados.** A matriz não autoriza `GRANT ALL`, ownership ao runtime, `BYPASSRLS`, nem memberships em roles privilegiadas.

### Lacunas antes de transformar a matriz em SQL

- Confirmar no DDL final se os IDs são fornecidos pela aplicação ou gerados por sequences; conceder `USAGE` em sequences somente onde necessário.
- Inspecionar triggers, funções, views, foreign keys e cascatas que possam exigir privilégios indiretos.
- Testar `SET ROLE`, memberships herdadas, owner bypass, `BYPASSRLS`, RLS habilitada/forçada e acesso por `PUBLIC`, `anon`, `authenticated` e `service_role`.
- Testar cada operação permitida e negada com conexões independentes por role no PostgreSQL descartável, inclusive rollback de auditoria e desativação de usuário.
- Resolver o lock de `usuarios` e a atomicidade entre atualização cadastral e INSERT em `audit_events` antes de qualquer separação de credenciais.

**Status:** matriz de código documentada; matriz de privilégios do banco ainda não aprovada. Nenhum DDL, grant, role, policy ou migration foi executado nesta etapa.

## 9. Dependências indiretas: sequences, triggers, funções e locks

Foi feita uma varredura estática dos quatro rascunhos SQL versionados nesta branch:
- `docs/sql-piloto-financeiro.sql`
- `docs/sql-controle-revisao-migracao-rascunho.sql`
- `docs/sql-controle-lotes-importacao-rascunho.sql`
- `docs/sql-auditoria-rascunho.sql`

Resultado observado nos arquivos atuais:

| Dependência | Evidência no DDL revisado | Consequência para privilégios |
|---|---|---|
| IDs por sequence/identity/serial | Não foram encontrados `SERIAL`, `IDENTITY`, `nextval` ou `CREATE SEQUENCE`; as PKs declaradas são `text`. | Não há concessão de `USAGE` em sequence justificada por esses DDLs. Reavaliar se uma migration futura introduzir sequence ou default gerador. |
| Triggers e funções próprias | Não foram encontrados `CREATE TRIGGER`, `CREATE FUNCTION` ou `CREATE PROCEDURE`. | Nenhum `EXECUTE` em função própria nem privilégio `TRIGGER` é justificado pelo DDL atual. Funções internas usadas pelo PostgreSQL e defaults como `now()` não significam que o runtime precise de grants amplos. |
| Exclusões em cascata | As FKs explícitas encontradas usam `ON DELETE RESTRICT`; não foi encontrada `ON DELETE CASCADE`. | Exclusões dependentes devem falhar enquanto houver referências. Testar cada FK com dados sintéticos e confirmar que nenhuma cascata remove histórico ou registros relacionados. |
| Atualizações em cascata | Não foi encontrada cláusula `ON UPDATE CASCADE`. | Não presumir propagação automática de alterações de chave. |
| Views/materialized views | Nenhuma definição foi encontrada nos quatro rascunhos examinados. | Não há grant de leitura em view justificado por esses arquivos. |
| Locks explícitos do backend | O código de administração de usuários usa `LOCK TABLE ... IN SHARE ROW EXCLUSIVE MODE`; fluxos de estoque e usuário também usam `SELECT ... FOR UPDATE`. | A matriz CRUD não prova que a role runtime consegue executar esses caminhos. Incluir testes de sessão real com a role candidata, em transações concorrentes e descartáveis. Não conceder ownership para contornar falha. |

### Escopo e limites da conclusão

Esta é uma inspeção estática dos rascunhos listados e do código dos adaptadores consultados, não uma inspeção de catálogo em banco com o schema Bravo instalado. Ela não prova que objetos equivalentes existam no banco, nem cobre objetos criados manualmente fora do repositório, extensões, funções instaladas por terceiros ou futuras migrations.

Os IDs textuais são fornecidos pela aplicação nos comandos INSERT dos adaptadores observados. Portanto, não se deve adicionar privilégios de sequence preventivamente. Se a estratégia de IDs mudar, atualizar primeiro o DDL, os adaptadores e esta matriz.

### Casos adicionais obrigatórios na futura homologação

1. Para cada FK com `ON DELETE RESTRICT`, inserir pai e filho sintéticos e provar que a exclusão do pai é recusada; depois remover os fixtures na própria base descartável.
2. Para `estoque` e `acertos_estoque`, provar que a role de runtime pode executar o fluxo transacional autorizado sem obter UPDATE/DELETE no histórico.
3. Para `usuarios`, testar `LOCK TABLE ... IN SHARE ROW EXCLUSIVE MODE`, `SELECT ... FOR UPDATE`, UPDATE e INSERT de auditoria na mesma transação, incluindo rollback quando a auditoria falhar.
4. Executar duas sessões concorrentes nos caminhos que usam locks e confirmar ausência de bypass por credenciais privilegiadas.
5. Repetir a varredura de sequences, triggers, funções, views e FKs depois de qualquer revisão do DDL, antes de aprovar grants.

**Status:** nenhum grant de sequence, EXECUTE, TRIGGER ou privilégio de ownership foi recomendado ou aplicado. O teste do lock de usuários continua pendente e é um bloqueio explícito para aprovar a role runtime.

## 10. Fronteiras transacionais reais: estoque, usuários e auditoria

A leitura conjunta de `storage.py`, `PostgresUnitOfWork`, dos adaptadores e dos serviços esclareceu um detalhe importante: compartilhar a mesma função `connection_factory` no composition root **não significa compartilhar uma conexão física**. Cada unidade de trabalho chama a fábrica e abre sua própria conexão; a conexão só é compartilhada quando o chamador a passa explicitamente a `append_in_transaction`.

### Fluxos confirmados no código

| Fluxo | Conexão/transação | Operações que precisam coexistir | Implicação |
|---|---|---|---|
| Movimento de estoque | Uma unidade de trabalho em `PostgresAcertosEstoqueRepository.register_movement` | SELECT/lock de `estoque`, UPDATE de saldo e INSERT em `acertos_estoque` | A role que executa movimento precisa dos privilégios efetivos nas duas tabelas na mesma transação. Não separar essas operações em fábricas/conexões independentes. |
| Edição cadastral de produto | Uma unidade de trabalho em `PostgresEstoqueRepository.replace` | SELECT FOR UPDATE em `estoque`, SELECT em `acertos_estoque`, UPDATE em `estoque` | Precisa de leitura do histórico para validar saldo; não precisa UPDATE/DELETE no histórico. |
| Desativação de usuário | Uma unidade de trabalho em `PostgresUsuariosRepository.deactivate_user` | LOCK/SELECT/UPDATE em `usuarios` e INSERT em `audit_events` via `append_in_transaction(connection, event)` | A mesma identidade SQL precisa executar todas as operações na mesma transação para manter atualização e auditoria atômicas. Falha no INSERT deve reverter a desativação. |
| Alteração administrativa de usuário | Uma unidade de trabalho em `PostgresUsuariosRepository.update_administrative_state` | LOCK/SELECT/contagem/UPDATE em `usuarios` e INSERT em `audit_events` na mesma conexão | Mesma restrição de identidade e atomicidade da desativação. |
| Auditoria independente | `PostgresAuditSink.append` abre sua própria unidade de trabalho | INSERT em `audit_events` | Adequado apenas quando o evento não precisa participar da transação de negócio do chamador. Não substitui `append_in_transaction` nos fluxos acima. |

### Consequências para desenho de roles

1. **Não separar o sink de auditoria por credencial apenas trocando sua connection factory.** Se o sink usar uma fábrica/role diferente, `append_in_transaction` ainda executará o INSERT com a conexão fornecida pelo repositório de usuários; a credencial do sink não é usada nesse método.
2. **Não converter auditoria transacional em chamada independente a `append`.** Isso permitiria que a mudança de usuário fosse confirmada sem o evento ou que o evento fosse confirmado sem a mudança, quebrando a garantia atômica já testada.
3. **Uma role única de API**, se escolhida, terá de reunir os privilégios mínimos necessários aos adaptadores de domínio e ao INSERT em `audit_events`. Isso é mais simples para a atomicidade atual, mas aumenta o conjunto agregado de privilégios da credencial.
4. **Separação de credenciais exige mudança arquitetural explícita.** Uma alternativa seria manter a mesma transação/conexão e aceitar uma role composta estritamente limitada aos dois objetos no fluxo administrativo; outra exigiria mecanismo transacional distribuído/outbox e tratamento de consistência. Nenhuma alternativa está implementada ou aprovada.
5. **O movimento de estoque não grava atualmente um evento em `audit_events` no método `register_movement`.** O histórico operacional é `acertos_estoque`; não presumir que o sink técnico registre esse fluxo até existir requisito e implementação explícitos.
6. **O sink independente não torna a auditoria geral obrigatória em toda operação.** A presença do objeto no composition root apenas injeta o serviço nos fluxos que o solicitam; não equivale a auditoria automática de todos os CRUDs.

### Testes de transação que devem constar do aceite

- Movimento de estoque: confirmar que falha no INSERT do acerto reverte o UPDATE do saldo; confirmar que concorrência no mesmo produto é serializada pelo lock de linha.
- Edição de produto: confirmar que a consulta ao histórico e a alteração cadastral observam a mesma transação e não permitem alterar saldo após movimento.
- Usuários: confirmar que falha de INSERT em `audit_events` reverte UPDATE de status/perfil; verificar lock de tabela com a role runtime candidata.
- Identidade SQL: registrar `session_user` e `current_user` em cada fluxo, sem credenciais em logs, para provar qual role efetivamente executa o INSERT de auditoria.
- Regressão: manter testes que verificam commit único, rollback em falha e idempotência de desativação.

**Decisão pendente:** a fronteira atual favorece uma identidade SQL transacional comum para domínio e auditoria de usuário, ou uma arquitetura transacional redesenhada antes de separar credenciais. Não conceder grants adicionais nem alterar connection factories para antecipar essa decisão.


## 11. Privilégios mínimos por operação e blast radius da role de API

A matriz CRUD anterior descreve verbos por tabela, mas ainda é grosseira para aprovar grants. A leitura dos comandos SQL mostra que algumas operações precisam de subconjuntos diferentes de colunas e que outras dependem de regras de negócio que um grant comum não consegue expressar.

### 11.1 Operações reais e escopo mínimo candidato

| Fluxo | Leitura necessária | Escrita necessária | Limite que o grant não garante |
|---|---|---|---|
| Listar/consultar produtos | Colunas projetadas por `PostgresEstoqueRepository._columns` | Nenhuma | Não restringe quais produtos o usuário da aplicação pode consultar; isso depende da autorização da aplicação/RLS. |
| Cadastrar produto | Nenhuma leitura explícita no INSERT | INSERT nas colunas fornecidas pelo adaptador: id, item, quantidade, minimo, maximo, etiqueta, foto_nome, foto_compactada_gzip, marca, linha, fabricante, data_cadastro | INSERT amplo permite criar produto com saldo inicial arbitrário; a regra de negócio precisa validar isso no serviço. |
| Editar cadastro do produto | quantidade em `estoque`; existência de movimento em `acertos_estoque`; SELECT FOR UPDATE no produto | UPDATE de campos cadastrais e também quantidade, updated_at e version pelo SQL atual | O grant não consegue dizer “quantidade só pode ser alterada se ainda não houver movimentos”. Essa condição hoje está no código Python. |
| Registrar movimento de estoque | SELECT quantidade e lock de linha em `estoque` | UPDATE de quantidade, updated_at, version em `estoque`; INSERT em `acertos_estoque` | A role que pode atualizar quantidade diretamente também pode tentar fazê-lo fora do fluxo de movimento. O grant não obriga o UPDATE a estar acompanhado do INSERT histórico. |
| Consultar histórico de estoque | Colunas de `acertos_estoque` usadas pela listagem/busca | Nenhuma | SELECT amplo permite leitura do histórico inteiro à identidade SQL; escopo por usuário/loja exige RLS ou autorização no serviço. |
| Criar usuário | Nenhuma leitura explícita no INSERT | INSERT em id, email, nome, loja, cargo, perfil, status | INSERT direto pode criar usuário com perfil/status arbitrário se o serviço não validar a operação. |
| Editar cadastro de usuário | SELECT usado por listagem/busca e verificações administrativas | UPDATE de email, nome, loja, cargo, perfil, status, updated_at e version no método replace | UPDATE de tabela permite alterar perfil e status, não apenas dados cadastrais. |
| Desativar usuário | LOCK da tabela; SELECT perfil/status por id com FOR UPDATE | UPDATE status, updated_at e version; INSERT em audit_events na mesma conexão/transação | Grant não impõe “não desativar a si próprio”, “não desativar o último Admin” nem atomicidade com auditoria fora da transação atual. |
| Alterar perfil/status administrativo | LOCK da tabela; SELECT de perfil/status e contagem de administradores ativos | UPDATE perfil, status, updated_at e version; INSERT em audit_events na mesma transação | Uma permissão UPDATE nesses campos também permite outras combinações de perfil/status se o caminho SQL puder ser chamado sem validação de serviço. |
| Registrar auditoria independente | Nenhuma | INSERT em audit_events | INSERT não prova que o evento representa uma ação legítima; a identidade do ator e o conteúdo precisam ser derivados/validados no backend. |

A tabela é um mapa de operações observadas, não uma lista pronta de GRANT. Antes de convertê-la em SQL, conferir novamente todas as colunas, predicates, joins e projeções de cada adaptador e os métodos de serviço que chamam cada operação.

### 11.2 Onde privilégios por coluna ajudam — e onde não ajudam

O PostgreSQL permite conceder SELECT, INSERT e UPDATE em colunas específicas. Isso pode reduzir o alcance de uma credencial em comparação com grants de tabela inteira. Exemplos para avaliação futura:

- O fluxo de movimento de estoque precisa atualizar `quantidade`, `updated_at` e `version`; a edição cadastral usa um conjunto maior de colunas.
- A desativação de usuário atualiza `status`, `updated_at` e `version`; a edição administrativa atualiza `perfil`, `status`, `updated_at` e `version`; o replace cadastral atualiza também email, nome, loja e cargo.
- INSERT por coluna pode restringir quais campos cada operação pode preencher, desde que o adaptador e os defaults do DDL sejam compatíveis.

**Limite essencial:** privilégios por coluna não criam identidades distintas por método. Se a mesma role receber a união dos privilégios necessários a todos os métodos, qualquer código executado com essa conexão poderá tentar usar essa união. Além disso, um grant de UPDATE na tabela inteira prevalece sobre a tentativa de restringir colunas por grants menores; a futura matriz deve evitar concessões de tabela mais amplas que anulem o recorte.

Privilégios por coluna também não expressam condições como “só atualizar saldo quando não existir histórico”, “não reduzir o número de administradores ativos”, “não alterar o próprio usuário” ou “só inserir auditoria correspondente à alteração da mesma transação”. Essas regras precisam continuar protegidas no serviço e, quando necessário, ser reforçadas por políticas/rotinas SQL desenhadas e testadas especificamente. RLS não substitui automaticamente validação de transições de estado.

### 11.3 Blast radius de uma única role de API

Uma role compartilhada pelos 15 repositórios de domínio, gestão de usuários e sink de auditoria acumularia a união dos privilégios necessários a todos esses fluxos. Se houver comprometimento dessa credencial ou execução indevida de SQL no backend, o impacto potencial não fica limitado ao módulo que originou a chamada.

Os limites mais importantes identificados:

1. **Estoque:** a role precisa de UPDATE no saldo para registrar movimentos e também INSERT no histórico. Com UPDATE amplo em `estoque`, o banco não distingue o caminho autorizado de movimento de uma alteração direta de saldo.
2. **Usuários:** a role precisa alterar perfil/status em operações administrativas e inserir auditoria atomicamente. Se também possuir UPDATE amplo para edição cadastral, a credencial consegue combinar alterações de campos que deveriam ter fluxos e validações diferentes.
3. **Auditoria:** INSERT em `audit_events` permite produzir eventos, mas não garante por si só que cada evento corresponda a uma operação real. A role não deve receber SELECT, UPDATE ou DELETE sem requisito separado.
4. **Domínio:** a união de CRUD dos demais repositórios aumenta o conjunto de tabelas acessíveis mesmo quando uma requisição utiliza apenas um módulo.
5. **RLS:** uma única identidade SQL compartilhada não separa automaticamente os limites de confiança entre módulos. Policies baseadas em identidade de sessão só ajudam se o contexto de usuário for autenticado, não for falsificável pelo cliente e for estabelecido de modo seguro em cada transação.

### 11.4 Alternativas arquiteturais para reduzir o alcance

| Alternativa | Benefício | Custo/risco | Situação |
|---|---|---|---|
| Uma role única de API com grants mínimos agregados | Preserva o modelo de conexão e as transações atômicas atuais; menor mudança inicial | Blast radius agregado; permissões de uma operação ficam disponíveis a todos os caminhos que compartilham a credencial | Possível, mas exige aceitar explicitamente o risco residual e provar os grants |
| Roles/fábricas por domínio ou fronteira de confiança | Reduz o conjunto de tabelas/colunas disponível em cada conexão | Exige separar composição e garantir que operações multi-repositório usem a mesma identidade/conexão quando precisam de atomicidade | Preferível para isolamento, mas não implementado |
| Rotinas SQL controladas para operações sensíveis | Pode expor apenas operações estreitas, como movimentar saldo ou desativar usuário com auditoria | Exige desenhar funções/rotinas, identidade do chamador, validação, ownership seguro e testes de RLS; EXECUTE passa a ser uma superfície privilegiada | Alternativa futura; não criar nesta etapa |
| Outbox/transação coordenada para separar auditoria | Pode separar credenciais e consumidores sem perder rastreabilidade eventual | Muda a semântica de atomicidade imediata, exige reprocessamento, idempotência e monitoramento | Não atende automaticamente ao contrato atômico atual; requer decisão de produto/arquitetura |

**Recomendação técnica para a próxima revisão:** não aprovar uma role única apenas com base na matriz CRUD. Primeiro classificar as operações sensíveis (movimento de estoque, edição de produto, desativação e alteração administrativa de usuários), decidir se o blast radius agregado é aceitável e comparar uma role única com credenciais separadas por fronteira. Se a role única for mantida, avaliar grants por coluna onde compatíveis e documentar explicitamente as regras que continuam dependendo do backend. Se houver separação, preservar uma única conexão/identidade dentro de cada transação atômica ou redesenhar formalmente o fluxo.

### 11.5 Testes adicionais obrigatórios antes de aprovar grants

- Para cada grant por coluna proposto, executar a operação permitida e provar que UPDATE/INSERT em colunas não concedidas falha.
- Provar que nenhum grant de tabela amplo neutraliza os grants por coluna.
- Testar `SELECT ... FOR UPDATE` e `LOCK TABLE ... IN SHARE ROW EXCLUSIVE MODE` com a role candidata, pois a compatibilidade dos locks não deve ser inferida somente da matriz CRUD.
- Provar que a role de movimento consegue executar UPDATE de saldo + INSERT de histórico atomicamente e que o INSERT falho reverte o saldo.
- Provar que nenhuma outra operação exposta à mesma role consegue alterar o saldo sem registrar histórico; se isso não puder ser garantido por grants, registrar a limitação e avaliar rotina SQL controlada.
- Provar que a role administrativa consegue desativar/alterar usuário e inserir auditoria na mesma transação, e que falha da auditoria reverte a alteração.
- Provar que operações de usuário sem autorização não podem alterar perfil/status mesmo que a role SQL tenha os privilégios técnicos necessários.
- Verificar `session_user` e `current_user` nos caminhos sensíveis, sem registrar credenciais ou tokens.
- Executar testes negativos de SELECT/INSERT/UPDATE/DELETE/TRUNCATE/DDL para cada identidade e verificar memberships transitivas e bypass de RLS.

**Status:** mapa de privilégios por operação e blast radius documentado; nenhuma role, grant, policy, função, migration ou connection factory foi criada/alterada. A decisão entre role agregada e separação por fronteira continua pendente de revisão explícita.
