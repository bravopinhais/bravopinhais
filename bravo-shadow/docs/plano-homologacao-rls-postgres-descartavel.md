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


## 12. Regras de negócio que hoje dependem da camada de serviço

A revisão dos serviços, schemas e routers de estoque, movimentos e usuários separou três fronteiras: validação do payload, autorização HTTP e integridade transacional do repositório. As proteções abaixo foram observadas no código da branch; não equivalem a garantias do PostgreSQL.

### 12.1 Estoque e movimentos

| Regra | Onde está protegida | Limite residual |
|---|---|---|
| Quantidade do movimento deve ser positiva; tipo deve ser Entrada/Saída | `AcertoInput` (Pydantic) | Validação de payload não protege INSERT SQL direto. |
| Saída não pode superar saldo | Serviço faz pré-checagem; `register_movement` relê quantidade com `FOR UPDATE` e recalcula saldo dentro da transação | A garantia concorrente está no adaptador transacional, não na pré-checagem do serviço. Testar com sessões reais. |
| Saldo e histórico devem ser gravados juntos | `PostgresAcertosEstoqueRepository.register_movement` atualiza `estoque` e insere `acertos_estoque` na mesma unidade de trabalho | Um grant UPDATE em `estoque` permite tentar alterar saldo por outros comandos com a mesma role; o banco ainda não obriga a existência do acerto correspondente. |
| Produto com movimento não pode ter saldo alterado pela edição cadastral | Serviço `EstoqueService.update` e, adicionalmente, `PostgresEstoqueRepository.replace` verifica histórico sob lock | A proteção Python não impede SQL direto. A verificação do repositório é mais forte para concorrência, mas também é código da aplicação. |
| Histórico não pode ser editado/excluído | Serviço e adaptador recusam replace/delete; não há rota DELETE no router | A garantia final deve ser ausência de UPDATE/DELETE na role SQL, e não apenas HTTP 405/409. |
| Produto com movimento não pode ser excluído | Serviço verifica referências; PostgreSQL possui FK RESTRICT para o histórico no DDL | O FK protege a integridade mesmo em SQL direto; a resposta HTTP amigável é camada de serviço. |

**Achado específico sobre `update_quantity`:** o método público de serviço altera a quantidade por `repository.replace` e não chama diretamente `_has_movement_references`. No caminho PostgreSQL, o `replace` do repositório repete a verificação de histórico e bloqueia alteração de saldo após movimento. No caminho em memória, o método é usado pelo serviço de movimentos, que atualiza saldo e adiciona o histórico em chamadas distintas. Portanto, ele não deve ser promovido a endpoint nem reutilizado como operação genérica de alteração de saldo; a API deve continuar expondo movimento como único fluxo de ajuste. Isso não é uma vulnerabilidade HTTP observada hoje, mas é uma restrição importante para futuras alterações.

O serviço de movimento faz uma leitura inicial do produto antes de chamar o repositório persistente. O repositório não confia nesse saldo inicial: adquire lock, relê o valor e calcula o novo saldo dentro da transação. Essa segunda leitura é a autoridade para concorrência. A consulta inicial serve para validações e construção do fluxo, não para garantir o saldo.

### 12.2 Cadastro e administração de usuários

| Regra | Onde está protegida | Limite residual |
|---|---|---|
| Cadastro comum sempre cria perfil Operador e status Ativo | `UsuarioCadastroInput` não aceita esses campos; `create_cadastral` fixa os valores | INSERT SQL direto com a role de API ainda pode definir perfil/status se os grants/rotinas permitirem. |
| Atualização cadastral não altera e-mail, perfil ou status | `UsuarioDadosCadastraisUpdateInput` aceita apenas nome, loja e cargo; `update_cadastral` preserva os demais campos | O método legado `update` aceita `UsuarioInput` completo; não está ligado à rota atual, mas não deve ser usado por novos endpoints cadastrais. |
| Auto-desativação e autoalteração de perfil/status são bloqueadas | `UsuariosService.deactivate` e `update_administrative_state` comparam e-mail autenticado ao alvo | A checagem é de serviço. O repositório também precisa preservar a proteção concorrente e o guard de último Admin. |
| Desativação e alteração administrativa exigem auditoria atômica | Serviço exige operação transacional; repositório chama `append_in_transaction` com a mesma conexão | A garantia depende da implementação e de que todos os chamadores usem esse caminho. SQL direto não herda a regra. |
| Exclusão física de usuário é proibida | Router e serviço respondem HTTP 410; adaptador não oferece delete | A role SQL também deve ficar sem DELETE em `usuarios`. |
| Alteração privilegiada não está exposta por rota | Router atual não declara endpoint para `update_administrative_state` | A ausência de rota é uma barreira atual, não uma autorização para criar endpoint futuro sem capability dedicada e revisão. |

**Ponto de atenção para a futura rota administrativa:** `update_administrative_state` aceita atualmente tanto um `AuthenticatedPrincipal` quanto os parâmetros separados `actor_subject` e `actor_email`. O método valida presença dos textos e impede alterar a própria conta, mas não verifica internamente que o principal tem perfil Admin ou capability específica. Hoje a operação não possui rota pública e a matriz de capabilities continua vazia/deny-by-default; portanto, não há endpoint administrativo habilitado. Antes de qualquer exposição, remover o caminho de identidade fornecida por strings arbitrárias e exigir principal autenticado validado + capability administrativa explícita na fronteira HTTP. Não ativar a capability nesta etapa.

A desativação também confia na autorização da rota para decidir quem pode executá-la: o serviço valida que o principal está ativo, tem subject/e-mail e não é o próprio alvo, mas não exige por conta própria perfil Admin. Manter a autorização explícita no router e testar 401/403 antes de qualquer liberação de capability.

### 12.3 Autorização HTTP observada

- Os routers de estoque e acertos usam `require_capability_dependency` para leitura, criação, atualização e exclusão aplicáveis.
- O router de usuários usa capabilities específicas para leitura, cadastro, atualização cadastral e desativação; a exclusão física termina em HTTP 410.
- Os testes verificam que Admin e Operador recebem 403 enquanto a matriz de capabilities não for aprovada.
- `ROLE_CAPABILITIES` permanece fechada por padrão. Nenhuma capability deve ser habilitada apenas porque existe uma rota ou teste com override.
- Os testes de serviço com principal sintético verificam regras de negócio, mas não substituem testes de autorização HTTP sem overrides nem testes de privilégios PostgreSQL com sessões independentes.

### 12.4 Requisitos de desenho antes de grants

1. Não conceder UPDATE amplo em `estoque` sem registrar que a role pode alterar saldo fora do fluxo de movimento; avaliar separar a credencial de movimentação ou encapsular a operação em rotina SQL restrita, com identidade e auditoria testadas.
2. Não conceder UPDATE amplo em `usuarios` sem registrar que a role pode alterar perfil/status por SQL direto. Avaliar grants por coluna, rotinas controladas ou separação de credenciais para cadastro comum e administração.
3. Manter `acertos_estoque` sem UPDATE/DELETE e `usuarios` sem DELETE no banco, além dos bloqueios da API.
4. Preservar a transação única de movimento saldo + histórico e de usuário + auditoria. Não trocar chamadas transacionais por commits independentes para simplificar grants.
5. Antes de expor alteração administrativa, exigir principal validado, capability administrativa separada, trilha de auditoria e testes negativos; hoje essa rota não existe e deve continuar assim.
6. Adicionar testes de contrato para garantir que nenhum router futuro use `EstoqueService.update_quantity` como endpoint de saldo e que nenhuma rota cadastral chame o método legado `UsuariosService.update`.
7. Testar em PostgreSQL descartável que a role candidata não consegue executar UPDATE/DELETE direto no histórico nem DELETE em usuários, e que as operações autorizadas continuam funcionando com os locks e transações atuais.

**Status:** mapeamento de regras de serviço e lacunas documentado. Nenhum endpoint foi adicionado, nenhuma capability foi ativada e nenhum grant, role, policy, função ou migration foi criado ou aplicado.


## 13. Auditoria da cobertura de testes transacionais e concorrência

A inspeção dos testes existentes separou testes de serviço, testes de adaptador com conexão simulada e integração com PostgreSQL real. Um teste com conexão simulada confirma a sequência de chamadas e o tratamento esperado do código, mas não comprova locks, isolamento, constraints ou rollback efetivo do servidor PostgreSQL.

### 13.1 Cobertura existente confirmada no código

| Área | Testes encontrados | Tipo de evidência | Limite |
|---|---|---|---|
| Movimento de estoque | Atualização de saldo + INSERT de histórico; saída sem saldo; produto inexistente; edição com/sem histórico; histórico imutável | Adaptador com conexão/cursor simulados em `test_postgres_inventory.py`; fluxos HTTP em memória em `test_estoque_acertos.py` | Não é integração real PostgreSQL; não comprova lock concorrente nem rollback provocado por falha do INSERT do histórico. |
| Alteração administrativa de usuário | Atualização + auditoria, último Admin, falha de auditoria, alvo inexistente | Testes de transação com conexão simulada | Não substitui a suíte de integração, mas cobre rapidamente caminhos e parâmetros. |
| Alteração administrativa real | Atualização e auditoria atômicas; bloqueio de último Admin; falha de auditoria com rollback; duas despromoções concorrentes | PostgreSQL descartável em `test_usuarios_admin_postgres_integration.py` | A fixture usa os DDLs de rascunho e executa DROP/CREATE de schema; só é permitida no banco local descartável explicitamente opt-in. |
| Desativação real | Desativação sem DELETE, auditoria atômica, bloqueio de último Admin e rollback após falha de auditoria | PostgreSQL descartável | Não há, nessa suíte, corrida concorrente de duas desativações/despromoções cruzadas além do teste de despromoção concorrente. |
| Privilégios/RLS reais | Script de inspeção de catálogo somente leitura executado em PostgreSQL 16 descartável vazio | CI valida sintaxe e execução das consultas de catálogo | O banco vazio não contém schema Bravo, roles específicas, grants, policies nem sessões de runtime; não valida autorização efetiva. |

### 13.2 Lacunas prioritárias em estoque

**P0 — rollback quando o INSERT do histórico falha após o UPDATE do saldo.** O teste atual de saldo insuficiente falha antes do UPDATE; portanto, não prova que uma falha na segunda escrita desfaz a primeira. Criar teste de integração PostgreSQL descartável que instale um trigger temporário de rejeição do INSERT em `acertos_estoque`, execute `register_movement`, espere erro e confirme em nova conexão que saldo e histórico permaneceram inalterados. Remover trigger/função em bloco `finally`.

**P0 — duas movimentações concorrentes sobre o mesmo produto.** Abrir duas conexões independentes, sincronizar o início e registrar movimentos que disputem o mesmo saldo. Verificar que o `SELECT ... FOR UPDATE` serializa os cálculos, que nenhum movimento é perdido, que saldo final corresponde à soma dos movimentos confirmados e que cada movimento confirmado possui exatamente um registro histórico. Incluir cenário em que uma saída concorrente excederia o saldo: apenas a combinação permitida deve confirmar.

**P1 — edição cadastral concorrente com movimento.** Executar edição de produto e movimento em conexões independentes. Confirmar que a ordem de locks não permite que a edição sobrescreva um saldo já movimentado nem que um movimento seja aplicado a um estado perdido. Validar o estado final e o histórico.

**P1 — tentativas diretas de mutação do histórico.** Com a role runtime candidata (quando existir e for aprovada), provar que UPDATE e DELETE em `acertos_estoque` falham no PostgreSQL, não apenas que a API responde 405/409. Não criar essa role nesta etapa.

### 13.3 Lacunas prioritárias em usuários e auditoria

**P1 — concorrência entre desativação e alteração administrativa.** Testar transações concorrentes que possam reduzir o conjunto de administradores ativos, incluindo uma desativação e uma despromoção em paralelo. A invariável esperada é manter pelo menos um Admin ativo, sem duplicar auditorias ou deixar atualização sem evento.

**P1 — idempotência concorrente da desativação.** Duas solicitações simultâneas para desativar o mesmo usuário devem produzir estado final Inativo e no máximo um evento de sucesso para a transição efetiva; a segunda chamada deve seguir o contrato idempotente já definido pelo repositório.

**P1 — integridade da trilha.** Confirmar que falhas de auditoria, erros de constraint e rollback deixam usuário e auditoria consistentes, e que não há evento de sucesso órfão ou duplicado.

**P2 — grants efetivos.** Quando houver desenho aprovado e roles candidatas no banco descartável, testar com sessões reais cada operação permitida e negada, incluindo locks, SELECT FOR UPDATE, UPDATE por coluna, INSERT, DELETE, TRUNCATE, DDL, memberships e bypass RLS. O teste não deve conectar-se a produção.

### 13.4 Condições para implementar a suíte de integração de estoque

- Reutilizar a guarda de banco descartável já aplicada na suíte de usuários: opt-in explícito, host local e nome exato `bravo_shadow_test`.
- Não executar contra produção, homologação compartilhada ou qualquer banco cujo nome/host não passe pela guarda.
- Usar DDL de estoque e auditoria em fixtures isoladas; evitar dependência da ordem de execução dos testes.
- Garantir limpeza de triggers/funções temporários em `finally` e limpeza do schema somente dentro do banco descartável protegido.
- Usar conexões físicas independentes para concorrência; não simular lock com um único objeto compartilhado.
- Fazer asserções de estado final por uma terceira conexão, depois do término das transações concorrentes.
- Manter testes determinísticos com barreiras/timeouts, sem depender de `sleep` como mecanismo de sincronização.
- Registrar separadamente resultado de teste unitário, integração real PostgreSQL e teste de privilégios; um não substitui o outro.

### 13.5 Critério de saída antes da aprovação de grants

Não considerar a fronteira de estoque comprovada até existir evidência PostgreSQL real para rollback do INSERT de histórico e concorrência de movimentos. Não considerar o modelo de usuário concluído até cobrir a corrida entre desativação e alteração administrativa e a idempotência concorrente. Não considerar RLS/grants validados com base apenas na execução do script de catálogo em banco vazio.

**Status:** auditoria estática dos testes concluída. As lacunas foram especificadas; nenhum teste novo foi executado ou criado nesta etapa, nenhum DDL foi aplicado e nenhum banco foi acessado.

## 14. Evidência de integração concorrente e limites ainda não homologados

### Execuções confirmadas

- Commit `e6faf3e6b1985a3c82c803fe9d06bbfe2ea3c208`: suíte de estoque em PostgreSQL descartável; workflow concluído com sucesso.
- Commit `58867a6154058e797d8eaf49243ef9c86535e4e9`: edição de produto concorrente com movimentação incluída; workflow concluído com sucesso. O log registrou **567 testes aprovados e 1 aviso**.
- Commit `a9b3ce1249b4f451cd9b4882dd1cac611a3204c9`: desativação concorrente de dois administradores incluída; workflow concluído com sucesso. O log registrou **568 testes aprovados e 1 aviso**.
- Execução do último commit: https://github.com/bravopinhais/bravopinhais/actions/runs/45991754931

### Cobertura confirmada no ambiente descartável

- Estoque: rollback do saldo quando a gravação do histórico falha.
- Estoque: duas saídas concorrentes não produzem saldo negativo nem histórico duplicado.
- Estoque: edição de produto e movimentação concorrentes preservam uma das ordens serializadas permitidas.
- Usuários: alteração administrativa concorrente preserva ao menos um Admin ativo.
- Usuários: desativação concorrente preserva ao menos um Admin ativo e grava somente a auditoria da operação confirmada.
- Usuários: falha na gravação de auditoria reverte a alteração administrativa ou a desativação.

### Limites desta evidência

Esses testes exercitam os adaptadores com conexões PostgreSQL reais e DDL de teste. Eles não comprovam o modelo final de privilégios, pois não executam a aplicação sob uma role runtime candidata nem homologam grants, memberships, policies ou bypass RLS.

Também não comprovam autenticação Google, identidade de sessão em produção, API pública para administração de usuários ou isolamento de credenciais. Esses itens permanecem pendentes e bloqueados até aprovação explícita do modelo de roles e da arquitetura de runtime.

Nenhuma migration foi aplicada a banco persistente. Nenhuma role, policy, grant ou membership do desenho final foi criada. O CI usa somente o PostgreSQL 16 efêmero `bravo_shadow_test`.

## 15. Matriz refinada de operações e identidade runtime

### 15.1 Evidência de código consultada

Revisão estática da branch `bravo-shadow` em:
- `backend/app/core/authorization.py`: catálogo de capacidades e matriz Admin/Operador vazia.
- `backend/app/core/storage.py`: modo PostgreSQL injeta a mesma `connection_factory` em todos os adaptadores e no `PostgresAuditSink`.
- Adaptadores `postgres_repositories.py`, `postgres_catalogs.py`, `postgres_cadastros.py`, `postgres_governance.py`, `postgres_inventory.py`, `postgres_usuarios.py` e `postgres_audit.py`.
- Routers de estoque, acertos de estoque e usuários.

A matriz abaixo descreve o SQL que os adaptadores atuais precisam executar, não os grants efetivamente instalados. Não há role runtime final nem policy homologada.

### 15.2 Matriz operacional derivada dos adaptadores

| Tabela | SELECT runtime | INSERT runtime | UPDATE runtime | DELETE runtime | Observação |
|---|---:|---:|---:|---:|---|
| `plano_contas` | Sim | Sim | Sim | Sim | CRUD; atualização otimista opcional |
| `financeiro` | Sim | Sim | Sim | Sim | CRUD e vínculo com plano de contas |
| `formas_monetarias` | Sim | Sim | Sim | Sim | CRUD de catálogo |
| `moradores` | Sim | Sim | Sim | Sim | Contém dados pessoais |
| `fornecedores` | Sim | Sim | Sim | Sim | Cadastro |
| `empregados` | Sim | Sim | Sim | Sim | Contém endereço, telefone e contato de emergência |
| `contas_bancarias` | Sim | Sim | Sim | Sim | Saldo cadastral; não é conciliação bancária |
| `condominio` | Sim | Sim | Sim | Não | Adaptador não oferece exclusão |
| `conselheiros` | Sim | Sim | Sim | Sim | Cadastro |
| `categorias` | Sim | Sim | Sim | Sim | Exclusão pode falhar por FK de documentos |
| `motivos_acerto` | Sim | Sim | Sim | Sim | Exclusão pode falhar por FK de movimentos |
| `documentos` | Sim | Sim | Sim | Sim | Guarda conteúdo/arquivo compactado no registro |
| `estoque` | Sim | Sim | Sim | Sim | UPDATE de saldo depende de fluxo protegido no serviço/adaptador |
| `acertos_estoque` | Sim | Sim | Não | Não | Histórico append-only; movimento insere registro |
| `usuarios` | Sim | Sim | Sim | Não | Exclusão física HTTP 410; desativação/admin usa UPDATE |
| `audit_events` | Não | Sim | Não | Não | Sink oferece INSERT; sem leitura/edição/exclusão |

### 15.3 Consequência para a role técnica

O composition root atual injeta uma única fábrica de conexões em todos os repositórios e no sink de auditoria. Portanto, a proposta de uma única role de API, se mantida, precisará acumular a união dos privilégios operacionais acima, inclusive UPDATE em `usuarios` e INSERT em `audit_events` na mesma conexão/transação quando ocorrer desativação ou alteração administrativa auditada.

A auditoria de negação de capacidade usa `PostgresAuditSink.append()`, com transação própria. A auditoria de sucesso da desativação/alteração administrativa usa `append_in_transaction(connection, event)` na mesma transação da alteração de usuário. Separar a credencial do sink sem redesenhar esse fluxo quebra a atomicidade atualmente implementada.

### 15.4 O que GRANT não consegue garantir

Privilégios de tabela não expressam as regras de negócio. Mesmo com UPDATE concedido em `estoque`, o banco não sabe, apenas pelo GRANT, que o saldo não pode ser alterado diretamente depois do primeiro movimento. Da mesma forma, UPDATE em `usuarios` não impõe por si só o bloqueio do último Admin, a proibição de auto-desativação ou a obrigação de registrar auditoria na mesma transação.

Essas condições continuam dependendo da camada de serviço e de transações testadas; se a ameaça inclui SQL arbitrário executado pela role da API, será necessário avaliar funções controladas, triggers/constraints ou uma separação de identidades com desenho transacional próprio. Nenhuma dessas alternativas foi implementada ou aprovada.

### 15.5 Limites de autorização HTTP

- `ROLE_CAPABILITIES` mantém Admin e Operador com conjuntos vazios; o comportamento atual é deny-by-default.
- As capacidades de usuários incluem leitura, cadastro, atualização cadastral e desativação; a rota administrativa de mudança de perfil/status não está exposta.
- O router de usuários bloqueia exclusão física com HTTP 410; a operação de desativação lógica exige `usuarios:deactivate`.
- Estoque exige capacidades distintas para leitura, criação, atualização e exclusão; acertos de estoque expõem leitura e criação, sem UPDATE/DELETE.
- O perfil funcional da aplicação não é uma role PostgreSQL e não deve ser usado diretamente como principal SQL.

### 15.6 Pendências antes de qualquer desenho executável

1. Aprovar se a primeira versão continuará com uma role técnica compartilhada ou se haverá separação por domínio/operação.
2. Definir como manter atomicidade entre alteração de usuário e INSERT de auditoria se houver mais de uma identidade SQL.
3. Definir se a proteção contra SQL arbitrário pela role da API faz parte do requisito de segurança.
4. Homologar privilégios por coluna/operação e políticas RLS em PostgreSQL descartável com sessões independentes.
5. Aprovar a matriz funcional Admin/Operador separadamente; ela continua vazia.
6. Só depois preparar uma proposta SQL para revisão. Este documento não autoriza executar DDL.

Nenhuma role, membership, policy, grant, função, trigger ou migration foi criada. Nenhum banco persistente ou remoto foi conectado ou alterado.

## 16. Comparação arquitetural de identidades PostgreSQL — 27/11/2026

### 16.1 Premissas verificadas no código

A fábrica em `backend/app/core/postgres_connection.py` abre uma conexão nova por chamada. `PostgresUnitOfWork` administra commit/rollback/close dessa conexão. O composition root injeta atualmente a mesma fábrica nos repositórios e no `PostgresAuditSink`.

A auditoria possui dois contratos distintos:
- `append(event)` abre uma unidade de trabalho própria, usada inclusive para registrar negações de autorização.
- `append_in_transaction(connection, event)` usa a conexão física recebida do repositório, sem commit/rollback/close. A desativação e a alteração administrativa de usuário dependem disso para manter alteração e auditoria na mesma transação.

Assim, trocar apenas a fábrica do sink por outra credencial não separa a identidade usada no INSERT transacional: nesse caminho, a operação continua usando a conexão do repositório de usuários.

### 16.2 Alternativa A — uma identidade runtime para os módulos da API

**Desenho:** uma role privada sem ownership, sem atributos administrativos e sem privilégios de migration; recebe somente os privilégios SQL necessários aos adaptadores runtime aprovados. Uma identidade distinta de owner/migrator permanece fora do processo web.

**Vantagens**
- Menor alteração no composition root e nas unidades de trabalho atuais.
- Mantém naturalmente a atomicidade de alteração de usuário + evento de auditoria.
- Menor número de secrets, pools, fábricas e caminhos operacionais.
- Menor custo inicial de testes e observabilidade.

**Riscos e limites**
- A role acumula a união dos privilégios de todos os módulos; uma injeção SQL ou comprometimento do processo pode alcançar essa união.
- RLS aplicada à role única limita o conjunto de tabelas/linhas acessíveis, mas não cria isolamento entre módulos do mesmo backend.
- GRANTs de tabela não expressam regras como último Admin, proibição de auto-desativação, nem a regra de saldo somente via movimentação.
- O runtime ainda precisa de INSERT em `audit_events` para manter a atomicidade atual, além de UPDATE em `usuarios` para operações administrativas.

**Adequação:** alternativa mais simples para uma primeira integração controlada, se o risco residual de uma identidade runtime compartilhada for explicitamente aceito e compensado por validação de entrada, autorização HTTP, queries parametrizadas, limites de rede, auditoria e testes.

### 16.3 Alternativa B — identidades runtime separadas por domínio/operação

**Desenho:** credenciais distintas para grupos de repositórios, por exemplo cadastros, financeiro, estoque e administração de usuários, com privilégios e pools independentes. A identidade de migration continua separada de todas as identidades runtime.

**Vantagens**
- Reduz o alcance de uma credencial comprometida ao conjunto de tabelas/operações daquele domínio.
- Permite revisar e rotacionar credenciais por domínio.
- Facilita demonstrar menor privilégio e atribuir operações a contextos técnicos específicos.

**Riscos e custos**
- Exige múltiplas fábricas/pools, seleção explícita de identidade por operação e testes que provem ausência de herança cruzada.
- A transação de desativação/alteração administrativa precisa atualizar `usuarios` e inserir `audit_events` atomicamente. Uma credencial de usuários sem INSERT em auditoria não consegue executar o fluxo atual.
- Conceder INSERT em auditoria à identidade de usuários mantém uma permissão cruzada intencional. Separar completamente exige redesenho, por exemplo uma função SQL estreita e cuidadosamente protegida que execute a mudança e o evento na mesma transação, ou um padrão outbox com semântica assíncrona e reconciliação.
- Uma função `SECURITY DEFINER` não é solução automática: exigiria owner não-runtime, `search_path` fixo, nomes qualificados, validação estrita de argumentos, EXECUTE mínimo e testes negativos de escalada.
- Um outbox assíncrono muda o significado de “auditoria gravada”: o evento pode estar pendente de publicação. Precisaria de idempotência, retry, monitoramento e política para falha permanente.
- Mais identidades aumentam a superfície de configuração, rotação, vazamento de segredo e erro de roteamento.

**Adequação:** melhor isolamento potencial, mas não é compatível como simples troca de configuração com a arquitetura transacional atual. Exige projeto de implementação e homologação próprios.

### 16.4 Comparação resumida

| Critério | A — runtime compartilhado | B — runtime por domínio |
|---|---|---|
| Complexidade inicial | Menor | Maior |
| Número de credenciais runtime | Uma | Várias |
| Blast radius de credencial | União dos módulos | Menor por domínio, se sem herança |
| Atomicidade usuário + auditoria | Preservada pelo fluxo atual | Exige privilégio cruzado ou redesenho |
| Rotação independente por domínio | Não | Sim |
| Mudanças no composition root | Pequenas | Relevantes |
| Testes de privilégio | Uma matriz runtime | Matriz por identidade e combinações |
| RLS | Escopo da identidade runtime | Escopo por role/domínio, se policies forem separadas |
| Adequação ao código atual | Mais próxima | Exige refatoração |

### 16.5 Direção técnica recomendada para avaliação

A recomendação de menor risco de mudança, **não uma autorização de implantação**, é evoluir em fases:

1. Manter owner/migrator fora do processo web em qualquer alternativa.
2. Para um primeiro piloto futuro, avaliar a alternativa A com role runtime sem ownership/BYPASSRLS/CREATEROLE/CREATEDB, sem DDL, com grants explícitos por tabela/operação e testes de negação em conexões independentes.
3. Registrar formalmente que essa primeira fase não oferece isolamento SQL entre módulos e que a credencial runtime possui o conjunto combinado de privilégios.
4. Antes de qualquer produção, decidir se esse risco residual é aceitável. Se não for, não liberar a alternativa A: projetar a alternativa B e resolver a atomicidade de auditoria antes de escrever DDL.
5. Não misturar a credencial de migration com qualquer identidade usada pelo servidor HTTP.

A alternativa B oferece melhor contenção em princípio, mas só se as credenciais não herdarem privilégios entre si e os fluxos transacionais forem redesenhados corretamente. Sem isso, a separação seria cosmética ou quebraria operações.

### 16.6 Decisões ainda não tomadas

- Não foi escolhida uma arquitetura final.
- Não foi aprovada a aceitação do blast radius da role runtime compartilhada.
- Não foi definido se a auditoria administrativa deverá usar função controlada, privilégio cruzado mínimo ou outbox.
- Não foram definidos nomes finais de roles, pools, grants, policies ou owners.
- Não foram criadas roles, memberships, grants, policies, funções, triggers ou migrations.
- Nenhum banco foi conectado ou alterado.

**Portão de segurança:** a comparação é documental. Qualquer fixture com roles privadas, teste de privilégios efetivos ou DDL de homologação exigirá autorização explícita prévia e permanecerá restrita ao PostgreSQL local descartável.

## 17. Auditoria transacional: função controlada versus outbox — 27/11/2026

### 17.1 Requisitos que não podem ser confundidos

O fluxo administrativo atual tem requisito síncrono: a alteração de perfil/status e o INSERT em `audit_events` ocorrem na mesma conexão e unidade de trabalho. Se o INSERT falha, a alteração deve sofrer rollback. O sink também registra negações autenticadas em uma transação independente; esse caminho não faz parte da transação de negócio.

Uma arquitetura futura deve declarar qual garantia oferece:
- **Atomicidade de negócio + evento:** ambos são confirmados ou revertidos juntos.
- **Entrega eventual:** negócio e intenção de auditoria são confirmados juntos; a publicação na tabela final ocorre depois e pode ficar pendente.

Não chamar a segunda garantia de auditoria síncrona nem ocultar atraso/falha de entrega.

### 17.2 Opção 1 — função SQL estreita com SECURITY DEFINER

**Conceito:** a API recebe apenas EXECUTE em uma função específica. A função, sob uma identidade proprietária não utilizável para login e com privilégios SQL estritamente limitados, executa a mudança administrativa e o INSERT em `audit_events` dentro da mesma transação PostgreSQL.

Fluxo conceitual:
1. Backend valida token Google, principal interno ativo, capacidade e regra de auto-alteração.
2. Backend chama a função com identificador do usuário alvo, novo perfil/status e campos mínimos do evento derivados do principal e do servidor.
3. Função valida estados/argumentos permitidos, bloqueia concorrência do último Admin, atualiza `usuarios` e insere `audit_events`.
4. Qualquer erro aborta a chamada; a transação do chamador não confirma parcialmente a alteração.

**Privilégios pretendidos (ainda não concedidos):**
- Role runtime: EXECUTE apenas na função; sem UPDATE direto em colunas administrativas de `usuarios` e sem INSERT direto em `audit_events` para esse fluxo.
- Owner da função: NOLOGIN, sem SUPERUSER/BYPASSRLS/CREATEDB/CREATEROLE, sem ownership de tabelas e com somente os privilégios necessários à função.
- Reader de auditoria: identidade separada, caso consulta seja aprovada.
- PUBLIC: EXECUTE revogado; conceder EXECUTE somente à role runtime aprovada.

**Controles obrigatórios de SECURITY DEFINER:**
- Definir `search_path` seguro e fixo na própria função (preferencialmente `pg_catalog` e schemas confiáveis explicitamente controlados); qualificar nomes de tabelas e objetos.
- Não usar SQL dinâmico concatenado; parametrizar todas as operações.
- Validar rigorosamente perfil, status, ação, tipo de entidade e correspondência do identificador do evento.
- Não aceitar subject Google, ator, request ID ou resultado como verdade autenticada do banco: esses dados são fornecidos pelo backend confiável e devem ser derivados/validados no servidor. A função não valida token Google.
- Não permitir ao chamador escolher ação arbitrária, gravar evento de outro tipo ou usar a função como INSERT genérico.
- Revogar EXECUTE de PUBLIC e revisar privilégios padrão, ownership, memberships e RLS.
- Testar chamadas malformadas, IDs de usuário arbitrários, elevação de perfil, último Admin, concorrência, falha no INSERT de auditoria e tentativa de chamar funções auxiliares.
- Manter a função pequena, específica e revisável. Uma função genérica com SQL dinâmico ou permissão administrativa ampla anularia o benefício.

**Vantagens**
- Preserva atomicidade estrita entre alteração administrativa e auditoria.
- A role da API não precisa de UPDATE administrativo direto nem INSERT em auditoria para esse fluxo.
- A fronteira de privilégio é explícita e pode ser testada no PostgreSQL.

**Riscos/custos**
- SECURITY DEFINER cria uma fronteira de confiança sensível: erro de ownership, search_path, EXECUTE ou validação pode virar escalada de privilégio.
- Regras passam a existir parcialmente no backend e parcialmente no SQL; é preciso evitar divergência e duplicidade.
- Migração, testes e observabilidade ficam mais complexos.
- O owner da função precisa ser cuidadosamente isolado e não pode ser a credencial web.

**Limite importante:** a função só reduz o privilégio se a API realmente perder os grants diretos equivalentes. Conceder EXECUTE e manter UPDATE/INSERT diretos não oferece contenção efetiva.

### 17.3 Opção 2 — outbox transacional e dispatcher separado

**Conceito:** a operação de negócio grava, na mesma transação, uma mensagem mínima em uma tabela outbox. Um worker independente lê a fila e grava o evento na tabela final `audit_events`.

Fluxo conceitual:
1. Backend valida principal e capacidade.
2. Uma única transação atualiza `usuarios` e insere o evento pendente em `audit_outbox`.
3. Commit confirma a mudança e a intenção de auditoria juntas.
4. Worker com identidade própria seleciona mensagens pendentes, publica em `audit_events` e marca a entrega.
5. Uma chave única/idempotente baseada em `event_id` evita duplicidade na tabela final.

**Privilégios pretendidos (ainda não concedidos):**
- Runtime de usuários: SELECT/UPDATE estritamente necessários em `usuarios` e INSERT apenas em `audit_outbox`; sem INSERT/UPDATE/DELETE em `audit_events`.
- Dispatcher: SELECT e atualização de estado/lease em `audit_outbox`, além de INSERT em `audit_events`; sem UPDATE/DELETE em `usuarios`.
- Reader: SELECT em auditoria somente se aprovado.
- Owner/migration: separado de runtime e dispatcher.

A tabela outbox pode ser desenhada como append-only com tentativas/entregas em tabela auxiliar, ou com colunas de estado atualizadas pelo dispatcher. A escolha afeta os grants: `FOR UPDATE SKIP LOCKED` e atualização de lease/status exigem privilégios de leitura e atualização cuidadosamente limitados. Não presumir que INSERT-only é suficiente para um worker com confirmação de entrega.

**Vantagens**
- A API não precisa escrever na tabela final de auditoria.
- O dispatcher pode ter credenciais e ciclo de vida separados do servidor web.
- Falhas temporárias na persistência final podem ser retentadas sem perder a intenção já confirmada na outbox.
- Permite controlar taxa, backoff, lote e isolamento do processamento.

**Riscos/custos**
- A auditoria final deixa de estar disponível imediatamente após o commit da operação.
- Falha permanente, backlog ou indisponibilidade do worker atrasam a entrega; exige alertas, métricas, política de retry e reconciliação.
- Entrega tende a ser pelo menos uma vez; precisa de idempotência e chave única.
- O estado da outbox cresce e exige retenção/arquivamento e controle de acesso.
- Se o requisito for “não confirmar alteração sem evento já gravado em audit_events”, outbox simples não satisfaz esse requisito. Ele garante intenção durável, não publicação síncrona na tabela final.

### 17.4 Comparação de garantias

| Critério | Função SQL controlada | Outbox + dispatcher |
|---|---|---|
| Negócio + auditoria final na mesma transação | Sim | Não; negócio + intenção ficam atômicos |
| API com INSERT direto em audit_events | Não precisa | Não precisa |
| API com UPDATE direto em usuarios | Pode ser removido para fluxo coberto | Necessário no desenho simples |
| Identidade separada para publicação final | Não é necessária | Sim |
| Disponibilidade imediata do evento final | Sim, após commit | Não garantida |
| Retentativa após falha transitória do destino | Não automaticamente | Sim |
| Complexidade de operação | Maior no desenho SQL seguro | Maior na operação do worker/fila |
| Risco principal | Escalada via SECURITY DEFINER mal configurada | Atraso, backlog, duplicidade e falha de entrega |

### 17.5 Direção recomendada para o requisito atual

Para o fluxo administrativo de usuários, o requisito registrado até agora é rollback da alteração quando a auditoria falha. Sob esse requisito, **a função SQL estreita é a opção mais alinhada**, desde que a função seja pequena, com owner NOLOGIN, EXECUTE mínimo, search_path fixo, sem SQL dinâmico e testes reais de privilégio em conexões independentes.

O outbox é uma alternativa válida se o responsável aceitar formalmente a garantia diferente: “a mudança só confirma quando a intenção de auditoria está durável na outbox; a publicação em audit_events é eventual”. Nesse caso, o produto precisa expor/monitorar pendências e ter processo de reconciliação. Não adotar outbox silenciosamente como substituto da atomicidade atual.

Uma decisão também pode ser híbrida por tipo de evento: eventos críticos administrativos síncronos via função controlada e eventos operacionais de alto volume via outbox, mas isso aumenta o número de contratos e não deve ser adotado sem requisitos de retenção, criticidade e disponibilidade definidos.

### 17.6 Plano de homologação futuro — ainda não autorizado

Em banco PostgreSQL local exclusivamente descartável, uma fase futura poderá:
1. Criar roles sintéticas NOLOGIN/LOGIN e schema de teste isolado, sem reutilizar nomes ou credenciais de qualquer ambiente persistente.
2. Implementar a função ou outbox em migration de teste separada, depois de autorização explícita.
3. Conectar com credenciais independentes para runtime, owner da função, dispatcher e reader.
4. Provar operações permitidas e negadas, incluindo acesso direto à tabela, EXECUTE, RLS, ownership, memberships e privilégios herdados.
5. Simular falha de INSERT em auditoria, rollback, concorrência de último Admin, repetição do mesmo evento, queda do worker e recuperação do backlog.
6. Confirmar que nenhuma credencial runtime consegue alterar função, grants, policies, roles ou schema.
7. Descartar integralmente o banco temporário ao final.

### 17.7 Estado e decisões pendentes

- A função SQL não foi criada.
- A tabela outbox não foi criada.
- Nenhum worker/dispatcher foi implementado.
- Nenhuma role, grant, policy, membership ou migration foi criada/aplicada.
- A preferência técnica pela função controlada é uma recomendação documental, não decisão de produto nem autorização de execução.
- A matriz Admin/Operador permanece vazia; os endpoints administrativos continuam protegidos por deny-by-default.
- Nenhum banco persistente, Supabase hospedado ou produção foi conectado ou alterado.

## 18. Contrato proposto da função administrativa controlada — 27/11/2026

**Status:** especificação conceitual para revisão. Não contém DDL executável e não autoriza criar função, role, policy, grant ou migration.

### 18.1 Escopo funcional mínimo

A primeira função deve cobrir somente a alteração administrativa de perfil/status de um usuário existente. Não deve ser uma função genérica de escrita, nem receber nome de tabela, coluna, SQL, JSON livre, ação arbitrária ou payload de auditoria.

Operações permitidas no contrato:
- alterar `perfil` somente entre `Admin` e `Operador`;
- alterar `status` somente entre `Ativo` e `Inativo`;
- não permitir exclusão física;
- não alterar e-mail, nome, loja, cargo ou identificador;
- impedir remoção/desativação do último Admin ativo;
- impedir autoalteração de perfil/status no backend, antes de chamar a função.

A função não deve ser criada para desativação lógica até que o fluxo específico seja revisado separadamente. O primeiro piloto recomendado é a alteração administrativa que hoje já exige evento de auditoria na mesma transação.

### 18.2 Assinatura conceitual

Uma assinatura estreita possível, sujeita à revisão do schema real e dos tipos existentes:

```text
bravo_shadow.admin_update_user(
  target_user_id,
  new_profile,
  new_status,
  actor_google_subject,
  request_id,
  event_id
)
```

- `target_user_id`: identificador interno do usuário alvo.
- `new_profile`: enumeração fechada `Admin` ou `Operador`.
- `new_status`: enumeração fechada `Ativo` ou `Inativo`.
- `actor_google_subject`: subject do principal Google validado no backend, nunca recebido diretamente do navegador.
- `request_id`: identificador gerado no middleware do servidor; pode ser nulo se o contrato de evento permitir.
- `event_id`: identificador técnico único gerado no backend para idempotência/diagnóstico.

A ação de auditoria deve ser constante dentro da função (`usuarios:update_administracao`), assim como `entity_type = 'usuario'` e `outcome = 'success'`. O identificador da entidade deve ser o próprio `target_user_id`. Timestamp deve ser produzido no banco com relógio UTC/timestamptz, não aceito do chamador. Não aceitar e-mail, perfil do ator, resultado, timestamp ou conteúdo livre como parâmetros.

A assinatura é ilustrativa: não foi confirmada a tipagem definitiva de `usuarios.id` nem do `event_id` na tabela final. Esses tipos devem ser conferidos antes de qualquer migration.

### 18.3 Fronteira de confiança do ator

O banco não valida por si só o token Google nessa proposta. A função recebe o subject que o backend confiável derivou de `AuthenticatedPrincipal`, após validar identidade, status cadastral e capacidade.

Regras obrigatórias:
- A rota futura deve exigir a capacidade administrativa específica; a matriz Admin/Operador permanece deny-by-default até aprovação.
- O serviço futuro deve receber somente `AuthenticatedPrincipal`, nunca `actor_subject`/e-mail independentes vindos de parâmetros HTTP ou de payload.
- O backend deve obter o subject do principal autenticado e validar a proibição de autoalteração usando o vínculo interno confiável.
- A função pode validar que o subject não é nulo/vazio e impor tamanho/formato razoável, mas isso **não prova autenticidade Google**.
- Não usar `SET LOCAL`, variável de sessão ou GUC como se fosse prova criptográfica do ator: a própria role runtime pode, em geral, definir valores de sessão. Isso só serve como contexto de correlação se o modelo de ameaça aceitar a confiança no backend.
- Se o requisito incluir resistência a um backend comprometido ou SQL arbitrário executado pela credencial runtime, o parâmetro actor não é suficiente. Será necessário um mecanismo verificável pelo banco (por exemplo, assertion assinada com chave fora do banco e validação criptográfica controlada) ou rever a fronteira de confiança. Isso é uma decisão arquitetural separada, não presumir que SECURITY DEFINER resolve.

### 18.4 Sequência transacional obrigatória

Dentro de uma única chamada/transação:
1. Validar todos os argumentos e rejeitar valores fora das enumerações.
2. Adquirir bloqueio que serialize alterações administrativas concorrentes. A estratégia deve proteger o cálculo do último Admin; não depender apenas de um SELECT sem lock.
3. Buscar o alvo sob bloqueio e retornar erro controlado se não existir.
4. Calcular se a operação remove um Admin ativo (Admin/Ativo para qualquer estado que não seja Admin/Ativo).
5. Se remover, contar Admins ativos dentro da mesma região serializada; rejeitar quando o total for menor ou igual a um.
6. Aplicar UPDATE somente se o estado realmente mudar, incrementando `version` e atualizando `updated_at` conforme o contrato existente.
7. Inserir o evento mínimo de auditoria na mesma transação, com ação/tipo/resultado fixos e ator/request/event IDs validados.
8. Retornar resultado mínimo; nunca devolver payload de auditoria ou dados desnecessários.
9. Qualquer falha no UPDATE ou INSERT deve abortar a transação completa. Não capturar erro de auditoria para continuar e não converter falha em sucesso.

A função não deve efetuar COMMIT/ROLLBACK próprio: a transação é controlada pela conexão chamadora. A chamada deve participar da unidade de trabalho existente.

### 18.5 Idempotência e concorrência

- Definir uma constraint UNIQUE para `event_id` no destino final antes de depender dela como chave idempotente; o draft atual precisa ser verificado quanto à existência dessa constraint.
- Uma repetição com o mesmo `event_id` não pode produzir uma segunda alteração administrativa nem um segundo evento contraditório. Definir se a repetição devolve o resultado original ou erro de conflito; não usar `ON CONFLICT DO NOTHING` sem verificar que o evento anterior corresponde exatamente à mesma operação.
- A proteção do último Admin deve ser testada com duas sessões independentes tentando remover Admins diferentes simultaneamente. Exatamente uma operação pode remover um Admin quando há dois ativos; a outra deve ser bloqueada, mantendo pelo menos um Admin ativo.
- Testar também duas chamadas concorrentes para o mesmo alvo e reenvio após timeout do cliente, pois o cliente pode não saber se o commit ocorreu.

### 18.6 Privilégios e RLS — desenho a validar

A função `SECURITY DEFINER` deve pertencer a uma role dedicada NOLOGIN, sem atributos administrativos, sem ser owner das tabelas e sem membership concedida à role runtime.

A role proprietária da função deve receber apenas os privilégios de tabela/coluna e as policies RLS estritamente necessários à operação. Como o draft prevê FORCE ROW LEVEL SECURITY, não presumir que o owner da função contornará RLS: a execução deve ser testada com a role definer efetiva e policies explícitas, limitadas ao objeto/ação. Não adicionar policy ampla ou `USING (true)` para fazer a função funcionar.

A role runtime:
- recebe EXECUTE apenas na assinatura aprovada;
- não recebe UPDATE direto em `usuarios` para as colunas administrativas cobertas;
- não recebe INSERT direto em `audit_events` para esse fluxo;
- não recebe membership na role definer;
- não recebe CREATE no schema, ownership, BYPASSRLS, SUPERUSER ou grants herdados equivalentes.

A role definer:
- não tem LOGIN;
- não tem CREATE ROLE, CREATEDB, SUPERUSER ou BYPASSRLS;
- não é proprietária do schema/tabelas;
- recebe somente UPDATE das colunas necessárias e INSERT na tabela de auditoria, mais permissões RLS correspondentes;
- não é compartilhada com outras funções de negócio.

A função deve fixar `search_path` para schemas confiáveis, qualificar todas as tabelas e funções, revogar EXECUTE de PUBLIC e conceder apenas à role runtime escolhida. Dependências futuras não podem ser resolvidas por objetos controlados por runtime.

### 18.7 Cenários negativos de homologação

Em sessões reais independentes, provar:
1. Runtime consegue executar a função aprovada.
2. Runtime não consegue UPDATE direto em `usuarios` nas colunas administrativas.
3. Runtime não consegue INSERT/UPDATE/DELETE/TRUNCATE direto em `audit_events`.
4. Runtime não consegue executar overloads ou funções auxiliares não autorizadas.
5. PUBLIC, anon, authenticated e service_role não conseguem executar a função nem acessar o schema privado.
6. Runtime não consegue assumir a role definer via SET ROLE, membership direta ou transitiva.
7. Role definer não consegue ler/escrever tabelas fora do escopo mínimo, criar objetos ou alterar grants.
8. Argumentos inválidos, subject vazio, ação/estado não permitido, alvo inexistente e evento inconsistente são rejeitados.
9. Falha forçada no INSERT de auditoria reverte integralmente a alteração administrativa.
10. Falha/timeout/repetição com o mesmo event_id não duplica ou contradiz a operação.
11. Corrida de último Admin preserva ao menos um Admin ativo.
12. Alteração de search_path da sessão não redireciona referências da função para objetos não confiáveis.

### 18.8 Critérios para sair da especificação

Antes de qualquer implementação, precisam ser aprovados:
- requisito de ameaça (backend confiável versus backend potencialmente comprometido);
- vínculo persistente de identidade Google `sub` ↔ usuário interno;
- tipo definitivo dos identificadores e constraint idempotente;
- estratégia de lock e comportamento de repetição;
- owner dedicado, grants de coluna, policies RLS da role definer e EXECUTE da role runtime;
- tratamento de erros SQL sem vazar detalhes ao cliente;
- testes de integração em PostgreSQL descartável com credenciais independentes;
- revisão de segurança independente da função e de todas as dependências.

**Nenhuma implementação foi autorizada ou executada nesta etapa.** A função, roles, policies, grants, migrations, vínculos de identidade e rotas continuam inexistentes/não ativados. A matriz de capacidades segue vazia.

## 19. Compatibilidade do contrato com o SQL e os adaptadores atuais — 27/11/2026

**Resultado:** compatibilidade estrutural parcial. O contrato cabe nos tipos e nas regras atuais, mas há bloqueios de RLS, fronteira de identidade e semântica de repetição que impedem implementação direta.

### 19.1 Compatibilidades confirmadas no código/DDL versionados

| Elemento | Evidência atual | Consequência para a função |
|---|---|---|
| Identificador do usuário | `usuarios.id` é `text PRIMARY KEY` | `target_user_id` deve ser `text` |
| Perfil | `text` com CHECK em `Admin`/`Operador` | A função deve repetir validação fechada, sem aceitar texto arbitrário |
| Status | `text` com CHECK em `Ativo`/`Inativo` | A função deve repetir validação fechada |
| Concorrência/versão | `updated_at timestamptz`, `version bigint` com default 1 | Atualização deve manter `updated_at = now()` e `version = version + 1` |
| Evento | `event_id text PRIMARY KEY` | Já existe unicidade técnica para detectar repetição de ID |
| Timestamp do evento | `occurred_at timestamptz NOT NULL` | Função pode produzir `now()`; o contrato não precisa receber timestamp |
| Ator | `actor_subject text NOT NULL` | Receber subject validado do backend; não é prova de identidade para o banco |
| Ação/entidade/resultado | Campos text e CHECK de `outcome` | A função pode fixar ação, entidade e resultado constantes |
| Request ID | `request_id text NULL` | Pode receber o identificador server-side já gerado pelo middleware |

O índice único `usuarios_email_ci_uidx` protege a unicidade do e-mail; a função administrativa não altera e-mail, portanto não precisa dessa regra para sua operação.

### 19.2 Divergências e lacunas que precisam ser resolvidas

**A. A função administrativa ainda não tem um ponto único de integração.**  
O método `PostgresUsuariosRepository.update_administrative_state` hoje executa diretamente `LOCK TABLE`, SELECT, contagem de Admins, UPDATE e `audit_sink.append_in_transaction`. Para usar a função, o repositório deverá substituir esse bloco por uma chamada parametrizada à função e interpretar o resultado/erros estáveis. Manter o UPDATE direto junto com EXECUTE anularia a redução de privilégio pretendida.

**B. O serviço aceita uma rota de ator legado insegura para esta futura operação.**  
`UsuariosService.update_administrative_state` ainda permite receber `actor_subject` e `actor_email` como strings independentes quando `actor` é omitido. Embora o método não esteja exposto por rota e a matriz continue deny-by-default, esse contrato deve ser removido antes da integração: aceitar exclusivamente `AuthenticatedPrincipal`, validar status ativo e derivar subject/e-mail do mesmo objeto. A função SQL não corrige essa lacuna do serviço.

**C. O banco não consegue provar que o subject veio do Google.**  
O SQL recebe um parâmetro `actor_google_subject`, mas não há vínculo persistente/claim assinada verificável no banco. A segurança depende do backend confiável e da autorização HTTP. Se o objetivo de ameaça incluir credencial runtime comprometida ou SQL arbitrário sob essa role, a função com parâmetro actor não atende sozinha; seria necessário um mecanismo de assertion verificável ou uma fronteira diferente.

**D. FORCE RLS impede presumir que SECURITY DEFINER contorna a política.**  
O rascunho de `audit_events` habilita e força RLS, mas não define policy. O DDL de usuários aplica RLS seletivamente a outras tabelas e não estabelece ainda a policy específica necessária para o executor da função. Portanto, a função não pode ser homologada apenas com GRANTs: será preciso decidir e testar a policy mínima para a role definer em `usuarios` e `audit_events`, mantendo negado o acesso direto da role runtime. Não usar BYPASSRLS, superuser ou policy aberta como solução.

**E. A chave primária do evento detecta duplicidade, mas não define idempotência de negócio.**  
`event_id PRIMARY KEY` faz uma segunda inserção com o mesmo ID falhar; não faz a função devolver automaticamente o resultado anterior. O contrato precisa decidir se uma repetição idêntica retorna resultado original ou conflito, e como detectar reutilização do mesmo ID com alvo/estado/ator diferentes. `request_id` não é chave única e não deve ser tratado como idempotency key sem decisão explícita.

**F. O bloqueio de último Admin precisa ser preservado dentro da função.**  
O repositório atual usa `LOCK TABLE usuarios IN SHARE ROW EXCLUSIVE MODE`, lê o alvo sob `FOR UPDATE`, conta Admins ativos e só então atualiza. Uma função futura deve preservar uma estratégia serializável equivalente ou provar outra estratégia com duas sessões independentes. Não substituir por uma contagem sem lock/serialização.

**G. A operação atual e o piloto proposto precisam de escopo definido.**  
O contrato da seção 18 escolheu inicialmente `update_administrative_state`. O método de desativação lógica `deactivate_user` é outro fluxo, com ação `usuarios:desativar` e request ID propagado. Não reutilizar a função administrativa para desativação nem presumir que ela cobre esse endpoint.

### 19.3 Ajustes necessários antes de implementar

1. Confirmar os tipos SQL exatos a partir do DDL versionado: todos os parâmetros de identificadores são `text`; não introduzir UUID SQL sem migração de contrato.
2. Definir comportamento de idempotência para `event_id` repetido e colisão/reuso com conteúdo divergente.
3. Definir policy RLS mínima para a role definer nas tabelas necessárias, considerando FORCE RLS; provar negação direta para runtime e roles padrão.
4. Remover do serviço a assinatura com `actor_subject`/`actor_email` independentes; aceitar somente principal autenticado.
5. Definir contrato de retorno/erros da função sem expor SQLSTATE/mensagem interna ao cliente.
6. Refatorar o repositório para chamar a função, sem caminho alternativo de UPDATE/INSERT direto no runtime.
7. Preservar regra de último Admin com lock/serialização e testar concorrência real.
8. Provar com credenciais independentes que runtime tem EXECUTE e não possui UPDATE administrativo/INSERT audit direto; role definer é NOLOGIN e não herdável por runtime.
9. Testar rollback quando INSERT falha, chamada repetida, evento conflitante, alvo inexistente, autoalteração, enumerações inválidas e acesso direto negado.

### 19.4 Decisão técnica após a inspeção

A estrutura de colunas existente é suficiente para um piloto sem alterar o modelo de dados: identificadores `text`, versão, timestamp e chave primária do evento já atendem ao contrato básico. **Não é necessário adicionar coluna ou tabela apenas para iniciar a função.**

Isso não significa que a função possa ser escrita agora. Os bloqueios reais são de segurança e semântica: policy RLS para executor sob FORCE RLS, confiança no ator, idempotência, retorno de erros e substituição do caminho SQL direto no repositório.

**Estado:** inspeção somente de arquivos versionados. Nenhum banco foi consultado; nenhum SQL foi executado; nenhuma função, policy, role, grant, migration ou alteração de código foi criada nesta etapa.

## 20. Matriz de privilégios efetivos — função administrativa controlada — 27/11/2026

**Status:** matriz-alvo para revisão, não grants executados. Os nomes abaixo são papéis conceituais; não criar roles com estes nomes sem aprovação.

### 20.1 Papéis conceituais e fronteiras

| Papel conceitual | Finalidade | Pode autenticar? | Fronteira |
|---|---|---:|---|
| `bravo_api_runtime` | Backend web/API | Sim | Chama apenas a assinatura administrativa aprovada; sem DML administrativo direto |
| `bravo_admin_fn_owner` | Proprietário dedicado da função | Não (NOLOGIN) | Privilégios mínimos para executar a operação dentro da função |
| `bravo_audit_reader` | Consulta de auditoria, se aprovada futuramente | Sim, somente serviço autorizado | SELECT separado; sem escrita |
| `bravo_migrator` | DDL e migrations controladas | Sim, apenas processo administrativo isolado | Nunca usado pela aplicação |
| `PUBLIC`, `anon`, `authenticated`, `service_role` | Papéis padrão/gerenciados | Conforme plataforma | Sem acesso ao schema privado ou EXECUTE da função |

Não criar writer separado para este fluxo se a própria função for a única fronteira de escrita. A função substitui o INSERT direto do runtime em `audit_events`; um writer independente só seria necessário para outros fluxos com requisitos distintos.

### 20.2 Matriz de privilégios SQL diretos pretendidos

Legenda: **P** = permitido; **N** = negado; **C** = condicionado a revisão/necessidade; **—** = não aplicável.

| Operação direta | API runtime | Function owner | Audit reader | Migrator | PUBLIC/anon/authenticated/service_role |
|---|---:|---:|---:|---:|---:|
| USAGE no schema privado | P mínimo | P mínimo | P se leitura aprovada | P controlado | N |
| SELECT em `usuarios` | C (somente o necessário ao fluxo geral) | P mínimo à função | N | C | N |
| UPDATE em colunas administrativas de `usuarios` | **N** | P mínimo | N | C em migration | N |
| INSERT em `audit_events` | **N** | P | N | C em migration | N |
| SELECT em `audit_events` | N por padrão | N por padrão | P, se aprovado | C | N |
| UPDATE/DELETE/TRUNCATE em `audit_events` | **N** | **N** | **N** | C somente em manutenção/retention aprovada | N |
| CREATE/ALTER/DROP no schema | N | N | N | P em ciclo controlado | N |
| CREATE/REPLACE/ALTER da função | N | N | N | P em ciclo controlado | N |
| EXECUTE da função administrativa | P, somente assinatura exata | N por padrão | N | C em teste controlado | N |
| SET ROLE para function owner/migrator | N | — | N | C conforme procedimento | N |

**Importante:** o acesso do owner às tabelas não deve ser mais amplo que o necessário para a função. Se a função exigir SELECT para ler o alvo/contar Admins, conceder somente o escopo necessário; avaliar GRANT por coluna para UPDATE. Não conceder privilégios de tabela inteira quando privilégios por coluna forem suficientes.

### 20.3 Matriz RLS pretendida para o fluxo administrativo

RLS e GRANT são barreiras cumulativas: a operação só funciona se ambas permitirem. O desenho precisa considerar explicitamente que `audit_events` usa `ENABLE ROW LEVEL SECURITY` e `FORCE ROW LEVEL SECURITY`.

| Tabela / policy futura | API runtime | Function owner | Audit reader | Papéis padrão |
|---|---|---|---|---|
| `usuarios` — SELECT | policy conforme leituras runtime aprovadas | SELECT apenas para alvo e contagem necessários | N | N |
| `usuarios` — UPDATE | sem policy de UPDATE administrativo | UPDATE somente nas colunas/linhas cobertas pela função | N | N |
| `audit_events` — INSERT | sem policy de INSERT direto | INSERT apenas para evento administrativo fixo | N | N |
| `audit_events` — SELECT | N | N | SELECT, se aprovado | N |
| `audit_events` — UPDATE/DELETE | N | N | N | N |

As expressões RLS concretas não estão definidas nesta matriz. Não usar `USING (true)` ou `WITH CHECK (true)` como atalho. Uma policy para o executor da função deve ser específica à role e ao comando, e não pode transformar a role definer em uma identidade com acesso irrestrito ao schema.

**Risco de desenho a resolver:** policy RLS não valida token Google. Se a função executa como owner dedicado, o banco confia no backend para fornecer o ator; uma chamada SQL direta sob a role runtime poderia tentar passar subject de outra pessoa. O grant EXECUTE reduz as operações disponíveis, mas não autentica o ator. Se isso estiver fora do threat model aceito, será necessário mecanismo de assertion verificável pelo banco antes de liberar a função.

### 20.4 Privilégios herdados e atributos que bloqueiam o aceite

A inspeção precisa comprovar o estado efetivo, incluindo memberships transitivas, privilégios herdados, ACLs de schema/tabela/função e atributos de role.

Bloqueadores absolutos para `bravo_api_runtime` e `bravo_admin_fn_owner`:
- SUPERUSER, BYPASSRLS, CREATEDB ou CREATEROLE;
- ownership de schema, tabelas ou funções fora do escopo;
- membership direta ou transitiva em migrator, owner, reader ou qualquer papel privilegiado;
- CREATE no schema privado;
- TRUNCATE, REFERENCES, TRIGGER ou DDL não necessários;
- EXECUTE em overloads/rotinas auxiliares não aprovados;
- privilégios herdados via PUBLIC ou default privileges que reabram acesso revogado.

A role `bravo_admin_fn_owner` deve ser NOLOGIN e não pode ser concedida como membership à API. A role runtime não pode alterar atributos, memberships, ACLs, policies, ownership ou definição da função.

### 20.5 Matriz de prova por sessão independente

| Teste com credencial própria | API runtime | Function owner (sessão de teste isolada) | Audit reader | anon/authenticated/service_role |
|---|---|---|---|---|
| Chamar função administrativa aprovada | P | N por padrão | N | N |
| UPDATE administrativo direto em `usuarios` | N | P somente dentro do escopo SQL/RLS mínimo | N | N |
| INSERT direto em `audit_events` | N | P somente para operação coberta | N | N |
| SELECT direto em `audit_events` | N | N por padrão | P, se aprovado | N |
| UPDATE/DELETE/TRUNCATE em `audit_events` | N | N | N | N |
| Criar/alterar função ou policy | N | N | N | N |
| SET ROLE para owner/migrator | N | N | N | N |
| Alterar search_path da sessão e redirecionar objeto da função | N | N | N | N |

A sessão de teste do function owner serve para provar seus limites de privilégio; não representa uma credencial que a aplicação receberá. A execução real da função deve ser testada por uma conexão independente como runtime.

### 20.6 Regras para interpretar os resultados

1. `GRANT EXECUTE` sem revogar UPDATE/INSERT direto não satisfaz o objetivo de redução de privilégio.
2. `REVOKE` isolado não prova negação se houver membership, privilégio herdado, ownership, PUBLIC ou superuser.
3. `FORCE ROW LEVEL SECURITY` não substitui a prova de atributos da role; superuser e BYPASSRLS continuam sendo exceções relevantes.
4. O owner da função não pode ser o owner das tabelas, superuser ou BYPASSRLS apenas para contornar policy.
5. A API não pode receber senha/DSN do function owner ou migrator.
6. A função não pode expor operação genérica, DDL ou execução SQL arbitrária.
7. Testar negações com conexões autenticadas como as próprias roles; `SET ROLE` é complementar, não substituto.
8. Repetir as consultas de catálogo depois da instalação do schema e das policies no PostgreSQL descartável; salvar evidências sem segredos.

### 20.7 Pendências que impedem fechar a matriz como desenho final

- Confirmar se leituras gerais da API em `usuarios` precisam de SELECT direto e qual coluna/linha.
- Confirmar se o executor SECURITY DEFINER poderá receber policies específicas sob FORCE RLS sem ampliar acesso.
- Decidir se a confiança no backend para o parâmetro actor é suficiente ou se assertion assinada é requisito.
- Definir grants por coluna e políticas RLS correspondentes com base no DDL real.
- Definir se consulta de auditoria existirá e qual capacidade/perfil poderá acessá-la.
- Validar a estratégia de idempotência e a semântica de erro antes de estabilizar a assinatura.

### 20.8 Estado

Esta seção descreve apenas privilégios pretendidos. Nenhuma role conceitual foi criada; nenhum GRANT/REVOKE foi aplicado; nenhuma policy foi escrita ou aplicada; nenhuma função foi criada; nenhuma credencial foi provisionada; nenhum banco foi conectado. A matriz de capacidades do produto continua deny-by-default.

## 21. Identidade do ator e fronteira de confiança — 27/11/2026

**Status:** análise de ameaça e decisão de arquitetura pendente. Nenhum mecanismo de assinatura, segredo ou validação foi implementado.

### 21.1 O que cada camada consegue provar

| Camada | Evidência que consegue validar | O que não prova sozinha |
|---|---|---|
| Navegador | Dados enviados pelo usuário e sessão visual | Identidade Google confiável; ator de auditoria |
| Backend | Assinatura/claims do ID token Google, issuer, audience, expiração e vínculo com cadastro interno, quando implementados corretamente | Integridade contra comprometimento total do próprio backend |
| PostgreSQL | Restrições de schema, integridade, transação, grants, RLS e argumentos recebidos | Que um texto actor_google_subject corresponde a um token Google válido |
| Função SECURITY DEFINER | Operação SQL estreita sob privilégios do owner | Autenticidade do ator se receber apenas um subject em texto |

Conclusão: actor_google_subject é confiável somente na medida em que a fronteira que o fornece é confiável. A função não deve ser descrita como validadora de token Google.

### 21.2 Ameaça A — navegador ou cliente malicioso

A defesa obrigatória é:
1. O backend valida o token Google, incluindo assinatura, issuer, audience e expiração.
2. O backend resolve o subject validado para o cadastro interno e confirma status/capacidade.
3. O ator é derivado exclusivamente de AuthenticatedPrincipal.subject.
4. Qualquer actor, actor_subject, e-mail, perfil ou reviewer enviado no body é ignorado ou rejeitado; nunca sobrescreve o principal.
5. A API gera request_id e event_id no servidor.
6. A chamada SQL recebe apenas os campos mínimos derivados do principal validado e do contexto do servidor.

Testes negativos obrigatórios: body com subject de outro usuário, e-mail de outro usuário, perfil Admin forjado, actor ausente ou extra; todos devem falhar ou ser ignorados sem alterar o ator registrado. O evento persistido deve conter exatamente o subject do principal validado.

**Resultado esperado:** o navegador não consegue escolher o ator da auditoria. Esse controle depende do backend e de sua validação Google, não da função SQL isoladamente.

### 21.3 Ameaça B — runtime/backend comprometido

Se a role runtime possui EXECUTE na função e pode enviar livremente actor_google_subject, um invasor que controle integralmente esse processo pode chamar a função passando o subject de outra pessoa. RLS e SECURITY DEFINER não resolvem esse problema: a função recebe um texto válido do ponto de vista do tipo SQL, mas sem prova criptográfica de origem.

O desenho atual, portanto, protege contra falsificação pelo cliente quando o backend está íntegro; não oferece, por si só, proteção contra comprometimento total do backend/runtime.

### 21.4 Alternativas para o limite de confiança

| Alternativa | Propriedade | Limite / custo |
|---|---|---|
| A. Confiar no backend validado | Simples; subject derivado do principal Google e chamada SQL restrita | Runtime comprometido pode falsificar o ator |
| B. Verificar JWT Google dentro do banco | Banco verifica assinatura/claims do token original | Complexidade de JWKS, rotação, audience/issuer, relógio, extensões e disponibilidade; token não deve ser armazenado em auditoria |
| C. Assertion interna assinada, verificada no banco | Banco verifica assinatura e claims de uma declaração curta | Exige emissor confiável, chave privada isolada do runtime, chave pública/rotação e proteção contra replay |
| D. Serviço de autorização/assinatura separado | Pode validar o token Google e emitir assertion vinculada à operação | Mais componentes, disponibilidade e operação; o serviço não pode aceitar subject arbitrário do runtime |

Uma assertion interna segura precisaria, no mínimo, vincular criptograficamente:
- subject Google validado;
- operação exata e recurso alvo;
- perfil/capacidade relevante, se aplicável;
- instante de emissão e expiração curta;
- identificador único anti-replay;
- audience destinada à função/serviço Bravo Shadow.

A função teria que verificar assinatura, audience, expiração, operação/alvo e uso único/replay dentro da transação. A chave privada não pode estar disponível à role SQL runtime nem ao navegador. Se a API puder pedir ao signer que assine qualquer subject sem validação independente do token, a separação não agrega a garantia pretendida.

### 21.5 Direção recomendada para o piloto descartável

Para o primeiro piloto local, manter a Alternativa A como hipótese explícita de confiança: backend é o validador de identidade Google; PostgreSQL protege a operação e reduz privilégios, mas não autentica independentemente o ator. O piloto não deve alegar resistência a comprometimento total do backend.

Antes de produção ou ambiente compartilhado, fazer decisão formal sobre o threat model:
- Se o risco de backend comprometido estiver fora do escopo aceito, documentar essa confiança e manter os controles de validação, capability, EXECUTE mínimo e auditoria.
- Se o banco precisar rejeitar chamadas de um runtime comprometido que tente falsificar o ator, não liberar a função com subject em texto como única evidência; projetar e homologar alternativa B, C ou D separadamente.

Não escolher JWT no banco ou assertion assinada por conveniência sem protótipo, revisão de chave, rotação, replay e testes negativos. Não adicionar segredo ao frontend, variáveis públicas, SQL versionado ou role runtime.

### 21.6 Critérios de teste e aceite

**Com backend íntegro:**
- Token Google inválido, expirado, issuer/audience incorretos: negar antes do SQL.
- Usuário interno inativo ou sem capability: negar antes do SQL.
- Subject/e-mail enviado no body não altera o ator.
- Evento registra subject do principal validado e IDs gerados no servidor.
- Falha na auditoria reverte integralmente a alteração administrativa.

**Com conexão SQL runtime independente:**
- EXECUTE não concede UPDATE/INSERT direto nas tabelas.
- Argumentos fora do contrato, IDs vazios e enumerações inválidas são rejeitados.
- Não há função genérica nem SQL dinâmico.
- Replay de assertion (se alternativa assinada for adotada) é rejeitado atomicamente.
- O runtime não consegue assumir a role owner nem acessar credencial/chave privada.

**Limite da prova:** testes de aplicação com principal sintético validam o contrato do serviço, mas não provam validação criptográfica Google real. Testes SQL com sessão runtime provam grants/RLS, mas não provam origem Google do subject. As duas evidências são distintas e ambas precisam ser registradas.

### 21.7 Estado e bloqueios

Nenhum token Google foi consultado ou armazenado. Nenhuma chave, segredo, assertion, serviço signer ou verificador JWT foi criado. Nenhuma função SQL, role, policy, grant ou migration foi implementada/aplicada. Nenhum banco foi conectado. A alternativa A é uma hipótese para piloto descartável, não uma autorização para produção; a proteção contra runtime comprometido permanece explicitamente não resolvida.

## 22. Contrato de idempotência da alteração administrativa — 27/11/2026

**Status:** decisão de contrato e lacunas registradas; sem implementação ou alteração de schema.

### 22.1 Evidência do estado atual

- `audit_events.event_id` é `PRIMARY KEY`; isso impede duas linhas com a mesma chave, mas não define replay sem efeito colateral.
- `PostgresAuditSink.append_in_transaction` executa INSERT e deixa a transação ao chamador. Uma colisão de chave não é tratada como retorno do resultado original.
- `PostgresUsuariosRepository.update_administrative_state` bloqueia a tabela de usuários, lê o alvo, verifica o último Admin, atualiza `perfil/status`, incrementa `version` e só depois insere auditoria.
- Portanto, se o mesmo `event_id` for repetido, a segunda tentativa pode executar o UPDATE antes de o INSERT falhar. O rollback da transação deve reverter esse UPDATE, mas o chamador recebe erro de unicidade, não um replay idempotente bem-sucedido.
- Os testes de integração PostgreSQL inspecionados cobrem atualização/auditoria atômicas, último Admin, rollback e concorrência; não foi localizado um teste de replay idempotente da alteração administrativa com o mesmo `event_id`.

A chave primária é uma proteção de duplicidade no ledger, não prova suficiente de idempotência da operação de negócio.

### 22.2 Contrato recomendado

Definir `event_id` como chave de idempotência da operação administrativa, com dois resultados distintos:

| Situação | Resultado esperado | Efeito no estado |
|---|---|---|
| Primeiro uso do ID | Executar alteração e inserir evento atomicamente | Uma única alteração e um evento |
| Repetição do mesmo ID e payload idêntico | Retornar resultado original com indicação de replay | Nenhuma nova alteração, incremento de versão ou evento |
| Mesmo ID com ator, alvo, ação, perfil/status ou request_id divergente | Conflito determinístico (HTTP 409 na camada HTTP) | Nenhuma alteração |
| Falha antes do commit | Erro; transação revertida | Nenhum evento/alteração parcial; retry pode executar |
| Timeout após commit, cliente sem resposta | Retry com mesmo ID retorna replay original | Sem segunda alteração |

O payload canônico deve incluir, no mínimo: nome/versionamento da operação, actor subject, target user ID, perfil solicitado, status solicitado e request ID conforme a semântica aprovada. Campos não incluídos no fingerprint não podem ser usados para distinguir requests conflitantes.

### 22.3 Lacuna do schema atual

O registro atual de auditoria contém `event_id`, actor, action, entity, outcome e request_id, mas não registra `perfil/status` solicitados nem fingerprint do payload. Assim, ao encontrar um `event_id` existente, a função não consegue provar que a repetição pediu exatamente o mesmo estado final. Comparar apenas actor/action/entity não detecta reutilização do mesmo ID para alterar o mesmo usuário de `Operador` para `Admin`, por exemplo.

**Conclusão:** para garantir replay idêntico versus reutilização divergente, será necessário persistir uma representação verificável do payload da operação. Opções a avaliar no piloto:
1. Adicionar ao evento um campo `payload_hash`/`operation_hash` calculado dentro da fronteira confiável a partir de uma serialização canônica, ou uma coluna JSONB com os campos imutáveis da solicitação.
2. Criar tabela de idempotência dedicada, com `event_id` como chave e os campos da operação/fingerprint, gravada na mesma transação da alteração e do evento de auditoria.

Não usar apenas `request_id` como chave idempotente: no schema ele é nullable e não unique. Não confiar em hash fornecido pelo navegador. Se optar por hash, definir algoritmo, codificação e canonicalização estáveis, e calcular/verificar no lado confiável; não presumir extensão PostgreSQL disponível sem verificar o ambiente descartável.

### 22.4 Ordem transacional da função futura

1. Validar todos os argumentos e construir a representação canônica/fingerprint.
2. Adquirir lock transacional que serialize chamadas administrativas concorrentes. Preservar a proteção atual do último Admin; a estratégia de lock precisa cobrir também a verificação de replay.
3. Consultar a chave de idempotência/evento existente.
4. Se existir e o fingerprint coincidir, retornar o resultado original com `replayed = true`, sem UPDATE, sem incrementar `version` e sem INSERT de novo evento.
5. Se existir e o fingerprint divergir, retornar conflito estável, sem mutação.
6. Se não existir, validar alvo e regra do último Admin, aplicar UPDATE e gravar o registro de idempotência e a auditoria na mesma transação.
7. Qualquer falha na escrita de idempotência ou auditoria deve abortar toda a operação.

A serialização e a constraint UNIQUE devem continuar sendo a defesa final contra corrida entre duas chamadas com o mesmo ID. A implementação precisa definir como tratar uma colisão concorrente após a leitura inicial; não capturar genericamente `unique_violation` e declarar replay sem comparar o fingerprint persistido.

### 22.5 Resposta da função e contrato HTTP

A função futura deve retornar campos estáveis e mínimos, por exemplo: `target_user_id`, `perfil`, `status`, `version`, `event_id` e `replayed`. Não retornar texto interno de exceção PostgreSQL. O backend converte conflito de reutilização de chave em HTTP 409; falha de infraestrutura permanece erro de serviço sem revelar SQLSTATE/detalhes internos.

No replay, devolver o resultado original armazenado, não o estado atual possivelmente alterado por uma operação posterior. Isso exige persistir os dados de resultado/version no registro idempotente ou provar que podem ser recuperados sem ambiguidade.

### 22.6 Testes de aceite obrigatórios

- Primeira chamada: exatamente um UPDATE, incremento único de version e um evento.
- Replay sequencial idêntico: mesmo resultado, `replayed=true`, version inalterada e uma linha de auditoria.
- Mesmo event_id com perfil diferente: conflito e nenhuma mutação.
- Mesmo event_id com status diferente: conflito e nenhuma mutação.
- Mesmo event_id com ator diferente: conflito e nenhuma mutação.
- Mesmo event_id com alvo/ação/request_id diferente: conflito e nenhuma mutação.
- Duas sessões concorrentes com o mesmo ID e payload idêntico: uma execução efetiva; a outra recebe replay do resultado original.
- Duas sessões concorrentes com o mesmo ID e payload divergente: uma execução efetiva e a outra conflito; nunca duas alterações/eventos.
- Falha forçada ao persistir fingerprint ou auditoria: rollback de usuário, versão, idempotência e evento.
- Timeout simulado após commit e retry com o mesmo ID: replay sem nova alteração.
- Corrida do último Admin continua preservando ao menos um Admin ativo, inclusive com retries.

### 22.7 Impacto no escopo e decisão pendente

A afirmação anterior de que o schema atual é suficiente vale para o contrato básico da função, mas não para idempotência forte com detecção de payload divergente e retorno do resultado original. Essa garantia exige persistência adicional (coluna ou tabela) ou uma limitação formal do contrato. Recomenda-se não implementar a função até escolher uma dessas opções e revisar a migration correspondente no banco PostgreSQL descartável.

Nenhuma migration, coluna, tabela, função, role, policy ou grant foi criada/aplicada. Nenhum banco foi conectado. Nenhum teste novo foi executado nesta revisão; a análise foi feita sobre arquivos versionados da branch.

## 23. Replay estável, fingerprint semântico e concorrência — 27/11/2026

**Status:** refinamento documental do contrato da seção 22. Não contém DDL executável e não autoriza alteração de schema ou banco.

### 23.1 Correção da composição do fingerprint

A seção 22 incluiu `request_id` entre os campos candidatos do payload canônico. Isso precisa ser refinado para separar identidade da operação de rastreamento HTTP:

- `event_id` é a chave de idempotência estável, criada uma vez para a intenção administrativa e reutilizada em todas as tentativas.
- O fingerprint representa somente a semântica da operação: versão do contrato, nome/ação fixa, actor subject validado, usuário alvo, perfil solicitado e status solicitado.
- `request_id` é metadado de rastreamento da primeira tentativa aceita. Pode mudar em uma nova tentativa HTTP e, por isso, **não participa do fingerprint** nem transforma um replay legítimo em conflito.
- O primeiro `request_id` pode ser preservado junto ao resultado original para auditoria e diagnóstico. Uma tentativa posterior pode ter seu próprio request ID nos logs HTTP, sem reescrever o evento original.
- O backend deve gerar e conservar o mesmo `event_id` ao repetir uma operação após timeout. Gerar um ID novo em cada retry elimina a proteção de idempotência.
- O fingerprint deve ser calculado na fronteira confiável, com serialização canônica e versionada. Não aceitar hash fornecido pelo navegador como prova.

Consequência: mesmo `event_id` + mesmo fingerprint semântico = replay; mesmo `event_id` + fingerprint diferente = conflito HTTP 409. Um request ID diferente, isoladamente, não é divergência semântica.

### 23.2 Persistir o resultado original, não reconstruir o estado atual

A resposta de replay não pode ser montada consultando apenas a linha atual de `usuarios`. Exemplo:

1. Evento A altera o usuário para `Admin/Ativo`, versão 8.
2. Uma operação posterior B altera o mesmo usuário para `Operador/Inativo`, versão 9.
3. Chega novamente o evento A.

O replay de A deve devolver exatamente o snapshot produzido por A — `Admin/Ativo`, versão 8 e o mesmo `event_id` — com `replayed=true`. Não deve devolver `Operador/Inativo`, versão 9, nem tentar restaurar o estado antigo.

Portanto, o registro idempotente precisa armazenar o resultado confirmado da primeira execução, no mínimo:
- identificador do usuário alvo;
- perfil e status resultantes;
- versão resultante;
- event_id;
- timestamp de conclusão da operação;
- request_id original, apenas como metadado de rastreamento, se necessário.

A resposta original deve ser persistida na mesma transação que atualiza `usuarios` e grava `audit_events`. Assim, não existe resultado idempotente confirmado sem a alteração e a auditoria correspondentes, nem alteração confirmada sem o snapshot que permite replay.

### 23.3 Alternativa preferida: tabela dedicada de idempotência

A recomendação é avaliar uma tabela privada dedicada, em vez de misturar estado de controle de execução com o ledger de auditoria imutável.

Campos conceituais (nomes/tipos ainda não aprovados):
- `event_id`: chave primária estável;
- `operation_name` e `contract_version`;
- `fingerprint` calculado no backend confiável, ou campos semânticos canônicos suficientes para comparação;
- `actor_subject` e `target_user_id`;
- `requested_profile` e `requested_status`;
- `result_profile`, `result_status` e `result_version`;
- `audit_event_id` e `completed_at`;
- `original_request_id`, opcional e não usado na comparação semântica.

A tabela deve ter restrições que impeçam estado concluído sem os campos mínimos do resultado. Não armazenar payload completo, e-mail, token Google ou dados pessoais que não sejam necessários para verificar a operação e reproduzir a resposta.

A tabela de idempotência é estado técnico de deduplicação; `audit_events` continua sendo o ledger append-only. As duas gravações pertencem à mesma transação. O identificador do evento deve manter correspondência inequívoca entre os dois registros.

Uma coluna adicional em `audit_events` também poderia guardar fingerprint e snapshot, mas acoplaria controle de replay ao modelo de auditoria. A tabela dedicada é preferível para manter responsabilidades separadas e permitir política de acesso/retention própria.

### 23.4 Reserva da chave e chamadas concorrentes

A implementação futura deve evitar a sequência vulnerável “atualiza usuário e só depois descobre que o event_id já existe”. A ordem conceitual recomendada é:

1. Validar o principal e os argumentos; construir o fingerprint semântico.
2. Tentar reservar `event_id` na tabela idempotente dentro da transação, usando a constraint UNIQUE/PRIMARY KEY como árbitro da concorrência.
3. Se a reserva for obtida, executar a validação do alvo e do último Admin, atualizar usuário, gravar auditoria e completar o snapshot idempotente antes do commit.
4. Se a reserva não for obtida porque outra transação confirmou a mesma chave, ler o registro confirmado e comparar o fingerprint. Igual: devolver o snapshot original como replay. Diferente: conflito sem mutação.
5. Se a transação vencedora falhar e fizer rollback, a reserva também desaparece; uma tentativa concorrente pode então assumir a chave e executar a operação.
6. Se a gravação da auditoria ou do snapshot falhar, reverter reserva, alteração de usuário e evento como uma unidade.

No PostgreSQL, a constraint única faz a tentativa concorrente aguardar a transação que reservou a mesma chave. Depois da colisão, a função precisa fazer uma leitura em comando/snapshot que consiga enxergar o registro confirmado e comparar o fingerprint. O desenho deve declarar o nível de isolamento esperado (preferencialmente READ COMMITTED para esse fluxo) e tratar explicitamente serialization failure/deadlock com retry seguro. Não capturar qualquer `unique_violation` e presumir replay.

A reserva provisória não deve ficar visível como operação concluída: a linha só se torna observável depois do commit, já com snapshot completo. Uma falha anterior ao commit reverte a reserva. Se o desenho precisar de estados internos, eles devem ser protegidos por constraints e não permitir que uma linha incompleta seja interpretada como resultado replayável.

### 23.5 Retenção e expiração da chave

Excluir o registro idempotente reabre a possibilidade de uma repetição antiga executar novamente a alteração. Para operações administrativas, a recomendação inicial é manter a chave e o snapshot pelo mesmo horizonte de retenção da auditoria, preferencialmente sem expiração automática.

Se houver requisito formal de retenção limitada, não apagar simplesmente a chave ao vencer o prazo. Manter um tombstone mínimo que impeça reexecução e responda que a chave expirou/não pode ser repetida, sem reconstruir nem executar a operação. A janela de retry e o comportamento de chave expirada precisam fazer parte do contrato HTTP.

### 23.6 Matriz de testes atualizada

- Replay sequencial idêntico com o mesmo event_id e request_id diferente: replay do snapshot original, sem UPDATE, incremento de versão ou novo evento.
- Reutilização do mesmo event_id com actor, alvo, ação, perfil ou status divergente: conflito 409, sem mutação.
- Operação posterior altera o mesmo usuário; replay antigo continua retornando o snapshot e a versão originais.
- Duas sessões concorrentes com mesma chave e mesmo fingerprint: uma execução efetiva e um replay do resultado confirmado.
- Duas sessões concorrentes com mesma chave e fingerprints diferentes: uma execução efetiva e um conflito.
- A transação que reservou a chave falha antes do commit: reserva, usuário, auditoria e snapshot sofrem rollback; outra tentativa pode executar.
- Falha na auditoria ou no snapshot: rollback integral.
- Retry depois de timeout pós-commit: resultado original recuperado, sem segunda alteração.
- Chave antiga retida/tombstone não pode ser reutilizada para executar uma nova operação.
- Replay não depende do estado atual de `usuarios` e não grava um segundo evento de sucesso.

### 23.7 Decisão e estado

Ajuste da seção 22: `request_id` não integra o fingerprint semântico; `event_id` permanece estável entre tentativas. O resultado original deve ser persistido, não reconstruído do cadastro atual. A tabela dedicada é a alternativa preferida para avaliação, ainda sujeita à revisão de schema, segurança, retention e contrato HTTP.

Nenhuma tabela/coluna, função, role, policy, grant ou migration foi criada. Nenhum SQL foi executado e nenhum banco foi conectado ou alterado. Esta etapa é exclusivamente documental.
## 24. Contrato HTTP, classificação de falhas e recuperação segura — 27/11/2026

**Status:** proposta documental para a futura integração da função administrativa. Nenhuma rota foi criada, nenhum endpoint foi exposto e nenhum comportamento foi ativado.

### 24.1 Princípios de resposta

A camada HTTP deve traduzir resultados de negócio e falhas técnicas para respostas estáveis, sem expor mensagens PostgreSQL, SQLSTATE bruto, nomes de tabelas, constraints, queries, credenciais ou stack traces.

O contrato deve distinguir:
- rejeição antes da operação, por identidade/autorização inválida;
- conflito de negócio, no qual a solicitação é válida, mas não pode ser aplicada;
- replay idempotente de operação já confirmada;
- falha transitória, que pode ser tentada novamente com a mesma chave;
- resultado incerto, quando a conexão cai e o backend não sabe se o commit foi concluído;
- falha permanente/interna, que exige investigação e não deve ser repetida indefinidamente.

A resposta não deve afirmar que a operação falhou apenas porque o cliente perdeu a conexão. Se o commit pode ter ocorrido, o resultado é **indeterminado até reconciliação pelo mesmo event_id**.

### 24.2 Mapeamento HTTP proposto

| Condição | HTTP | Código estável sugerido | Comportamento |
|---|---:|---|---|
| Principal ausente, inválido ou expirado | 401 | authentication_required | Não chamar a função |
| Principal autenticado sem capacidade aprovada | 403 | capability_denied | Não chamar a função |
| Autoalteração proibida | 403 | self_administration_forbidden | Não chamar a função |
| Usuário alvo inexistente | 404 | target_not_found | Sem alteração ou evento de sucesso |
| Perfil/status fora do contrato | 422 | invalid_administrative_state | Rejeitar antes da mutação |
| Último Admin seria removido/desativado | 409 | last_active_admin_conflict | Sem mutação |
| Mesmo event_id com fingerprint diferente | 409 | idempotency_key_conflict | Sem mutação |
| Chave expirada/tombstone, se retenção limitada for aprovada | 409 | idempotency_key_expired | Não reexecutar |
| Replay idêntico | 200 | replayed=true | Devolver snapshot original |
| Primeira execução confirmada | 200 | replayed=false | Devolver snapshot confirmado |
| Dependência temporariamente indisponível antes de resultado conhecido | 503 | temporarily_unavailable | Retry limitado com o mesmo event_id |
| Commit de resultado incerto por queda de conexão/timeout | 503 | operation_outcome_unknown | Consultar/repetir com o mesmo event_id; nunca gerar outro |
| Falha interna não classificada | 500 | internal_error | Não revelar detalhes; correlacionar por request_id |

O status 200 para primeira execução e replay evita que clientes interpretem um replay bem-sucedido como criação de recurso. Se o contrato REST final preferir 201 para primeira execução, a distinção deve ser documentada e mantida estável; replay continua retornando o resultado original sem afirmar nova criação.

### 24.3 Envelope de resposta

Formato conceitual, ainda não implementado:

- Sucesso: data com target_user_id, perfil, status, version, event_id, replayed e completed_at.
- Erro: error.code estável, mensagem pública curta e request_id da tentativa HTTP atual.
- O resultado original preserva o request ID da primeira execução no registro de idempotência/auditoria, se necessário para rastreabilidade; o envelope da tentativa atual pode informar seu próprio request ID.
- Não incluir actor subject, e-mail, token, fingerprint bruto, SQLSTATE ou conteúdo interno da exceção no corpo público.

Em replay, data reproduz o snapshot da operação original. O campo replayed muda para true, pois descreve a tentativa atual; os demais campos de resultado permanecem os originalmente confirmados.

### 24.4 Política de retry por classe de falha

**Pode admitir retry automático limitado, sempre com o mesmo event_id:**
- indisponibilidade transitória de conexão antes de a operação produzir resultado;
- deadlock ou falha de serialização, depois de rollback confirmado;
- timeout de aquisição de conexão;
- indisponibilidade temporária do serviço de banco.

**Exige reconciliação pelo mesmo event_id antes de declarar falha:**
- timeout durante a chamada;
- reset de conexão enquanto o comando está em execução;
- perda de conexão durante COMMIT;
- resposta perdida depois de o PostgreSQL confirmar a transação.

Nesses casos, o backend não deve gerar outra chave nem tentar compensar com UPDATE inverso. Deve consultar/repetir a mesma operação idempotente. Se a transação anterior confirmou, recebe o snapshot como replay; se reverteu, a chave não estará concluída e a tentativa poderá executar; se o banco continuar indisponível, manter o resultado como desconhecido.

**Não repetir automaticamente:**
- 401/403;
- 404;
- 409 de último Admin ou fingerprint divergente;
- 422;
- falha de validação/contrato;
- erro interno sem classificação confiável.

Retries automáticos devem ter limite, backoff exponencial com jitter, timeout total e logs correlacionados. Não manter retry infinito em processo HTTP. Depois do limite, responder 503 com código estável e orientação de reconciliação pelo mesmo event_id.

### 24.5 Classificação interna de erros PostgreSQL

O adaptador pode usar SQLSTATE e contexto da operação internamente, mas a tradução deve ser explícita e restrita ao fluxo administrativo.

- 40001 (serialization failure) e 40P01 (deadlock): retry transacional limitado, com o mesmo event_id; só repetir automaticamente quando a transação anterior tiver sido revertida.
- 55P03 (lock not available), se houver lock com timeout configurado: falha temporária, sem mutação confirmada; retry limitado.
- 57014 (query canceled): tratar com cautela; o cancelamento não prova por si só que nenhuma confirmação ocorreu em outra etapa. Se o resultado do commit for incerto, reconciliar pela chave.
- 23505: não converter genericamente em replay. Identificar a constraint exata. Colisão da chave idempotente exige leitura e comparação do fingerprint; outra constraint pode representar conflito de domínio ou erro interno.
- Falha no INSERT de auditoria ou no snapshot idempotente: propagar para abortar a transação inteira; classificar externamente como indisponibilidade/falha de serviço, sem revelar a causa SQL.
- Falha de autenticação/autorização é decidida no backend antes do SQL; não transformar qualquer erro SQL em 401/403.

A lista é uma base de classificação, não um mapeamento completo de todas as exceções do driver. A implementação deverá testar o driver/versão efetivamente escolhidos e preservar a causa interna nos logs protegidos.

### 24.6 Requisitos transacionais e de observabilidade

1. A função executa dentro da transação aberta pelo chamador; não executa COMMIT/ROLLBACK próprio.
2. Alteração de usuário, evento de auditoria e snapshot idempotente confirmam ou revertem juntos.
3. O backend só responde sucesso depois de saber que o commit foi confirmado ou de recuperar o resultado persistido pelo mesmo event_id.
4. Em erro, o backend não tenta escrever um evento de sucesso separado depois da falha da transação.
5. Eventos de negação/autorização continuam sendo um fluxo distinto; a falha ao registrar negação não pode ser confundida com falha de auditoria da alteração administrativa.
6. Logs estruturados correlacionam request_id, event_id, operação, resultado/replay e classe de falha; não registram tokens, segredos, e-mails desnecessários nem payload pessoal completo.
7. Métricas devem distinguir execução nova, replay, fingerprint conflitante, retry, resultado desconhecido, rollback por auditoria e indisponibilidade.
8. Alertar sobre crescimento de retries, taxa de 409, operação em estado desconhecido e falha de gravação do ledger.
9. O cliente não deve apresentar “alteração concluída” até receber confirmação/reconciliação; para resultado desconhecido, exibir estado pendente de confirmação, sem instruir o usuário a criar outra operação.

### 24.7 Testes de aceite adicionais

- 401/403 são produzidos antes da chamada SQL.
- 404, 409 e 422 têm códigos estáveis e não revelam detalhes internos.
- Último Admin e fingerprint divergente não são retentados automaticamente.
- Deadlock/serialization failure com rollback confirmado é repetido com o mesmo event_id.
- Timeout antes do commit permite retry idempotente sem duplicar evento.
- Queda após commit e antes da resposta é reconciliada como replay com snapshot original.
- Indisponibilidade persistente termina em 503 controlado, sem gerar nova chave.
- Falha de auditoria e falha de snapshot provocam rollback integral.
- SQLSTATE, query, nome de constraint e stack trace não aparecem no corpo HTTP.
- Logs correlacionam tentativa atual e operação original sem expor dados pessoais ou segredos.
- Replay com request_id diferente retorna o mesmo resultado de negócio e não grava novo evento.

### 24.8 Bloqueios e estado

Antes da implementação ainda será necessário fechar a assinatura/retorno SQL, os códigos de erro internos, o nível de isolamento, a política de timeout/lock, o envelope HTTP e a estratégia de retry do driver. A rota administrativa segue não exposta e as capacidades seguem deny-by-default.

Nenhum endpoint, função, middleware, retry automático, log ou métrica foi implementado nesta etapa. Nenhuma migration/DDL foi executada; nenhum banco persistente foi conectado ou alterado.

