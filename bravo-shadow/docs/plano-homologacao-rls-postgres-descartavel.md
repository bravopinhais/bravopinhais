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
