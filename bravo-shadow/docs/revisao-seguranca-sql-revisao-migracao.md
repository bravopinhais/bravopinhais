# Revisão de segurança SQL — revisão de migração Bravo Shadow

**Status:** parecer técnico; não aplicado. Nenhuma role, policy, grant ou migration foi criada.
**Escopo:** revisão estática do rascunho `sql-controle-revisao-migracao-rascunho.sql` e do adaptador `PostgresReviewLedgerStore`.

## 1. Separação obrigatória de papéis

O desenho final deve separar pelo menos:

- **Owner/migration role:** proprietária do schema e das tabelas; usada apenas em migrations locais aprovadas.
- **Runtime role:** identidade de conexão do backend; não é superuser, não tem `BYPASSRLS`, não é proprietária das tabelas e não pode criar/alterar schema, tabelas, policies ou grants.
- **Identidades de usuário:** continuam sendo validadas pela autenticação Google no backend; não são roles PostgreSQL individuais.

Não usar `service_role` do Supabase como atalho para o backend. Não conceder acesso direto às tabelas a `anon` ou `authenticated`.

## 2. RLS e propriedade das tabelas

O rascunho habilita RLS e não cria policies permissivas, o que é uma boa postura inicial de bloqueio. Porém, no PostgreSQL, o proprietário da tabela normalmente pode ignorar RLS, a menos que seja usado `FORCE ROW LEVEL SECURITY`; superusers e roles com `BYPASSRLS` também podem ignorá-la.

Antes de habilitar qualquer acesso:
1. Aplicar `FORCE ROW LEVEL SECURITY` nas três tabelas.
2. Garantir que a role de runtime não seja owner, superuser nem `BYPASSRLS`.
3. Manter a role de migration separada e sem uso pela aplicação.
4. Criar policies somente após escolher formalmente a estratégia de autorização.
5. Testar com as roles reais, incluindo tentativas de leitura, inserção, atualização e exclusão.

RLS sem policies e sem grants permanece fechado; não adicionar policies genéricas para “fazer funcionar”.

## 3. Integridade do esquema

O rascunho já contém boas proteções: FK composta lote/decisão, unicidade de versão por decisão, choices enumeradas, justificativa não vazia e bloqueio de UPDATE/DELETE como regra de grants ainda pendente.

Ajustes a considerar antes de uma migration:
- Preferir `text` com `CHECK (manifest_hash ~ '^[0-9a-f]{64}$')` em vez de `char(64)`, evitando semântica de preenchimento de espaços.
- Avaliar se `decision_id` deve ser PK global ou se a chave primária deve ser composta por lote e decisão. A unicidade global só é correta se o gerador garantir IDs globalmente únicos; a FK e o adaptador já tratam a identidade como pertencente ao lote.
- Adicionar validações de não vazio para `event_id`, `decision_id`, `decision_kind`, `decision_status` e `batch_key`.
- Manter `automatic_action = 'none'` enquanto este ledger for exclusivamente de revisão; nenhuma escolha deve executar importação.
- Considerar constraints para impedir divergência entre o manifesto do lote, o manifesto da decisão e o manifesto do evento. A FK atual não garante igualdade do hash entre as três tabelas.

## 4. Observação sobre o adaptador Python

O método `append` recebe `reviewer_id` como argumento textual. Isso é aceitável apenas como API interna de infraestrutura; não pode ser exposto diretamente por endpoint nem receber valor confiado do navegador.

Na futura camada de serviço:
- autenticar com `get_current_principal`;
- autorizar uma capacidade específica de revisão, ainda não aprovada;
- preencher `reviewer_id` com `principal.subject` no servidor;
- não aceitar `reviewer_id`, perfil ou status enviados pelo cliente;
- manter a inicialização do snapshot fora de endpoints públicos.

A capacidade de revisão não deve ser concedida automaticamente ao perfil Admin até aprovação explícita da matriz de permissões.

## 5. Plano mínimo de testes locais

Executar somente em PostgreSQL local descartável, com dados sintéticos:

1. Runtime role não consegue criar schema/tabela ou alterar policies.
2. Runtime role não é owner, superuser nem possui `BYPASSRLS`.
3. Sem policy/grant, leitura e escrita falham.
4. Owner e runtime são testados separadamente com RLS forçada.
5. `anon`, `authenticated` e `service_role` não obtêm acesso às tabelas privadas.
6. Runtime consegue apenas as operações explicitamente concedidas.
7. UPDATE e DELETE de eventos falham inclusive por SQL direto da runtime role.
8. Hash divergente entre lote, decisão e evento é rejeitado.
9. Acesso cruzado entre lotes é negado.
10. Duas conexões concorrentes tentando gravar a mesma versão resultam em apenas uma gravação.
11. Falha durante INSERT causa rollback completo.
12. O ator persistido é o `subject` do principal autenticado, nunca um identificador arbitrário do request.

Os mocks Python não substituem esses testes. Eles ainda precisam ser executados com PostgreSQL local e roles reais.

## 6. Portões que continuam fechados

- Não conectar a banco de produção.
- Não usar dados reais ou o payload legado para testes.
- Não executar o SQL atual.
- Não aplicar migrations locais até revisão do SQL final e aprovação dos papéis.
- Não criar policies/grants até a estratégia RLS e a matriz de permissões estarem aprovadas.
- Não iniciar importação, dual-write ou cutover.

## Conclusão

O rascunho é uma base conservadora, mas ainda não está pronto para aplicação. Os pontos mais importantes a resolver são: separar owner/runtime, forçar RLS, garantir igualdade dos hashes por constraints e ligar o ator da revisão ao principal autenticado em uma camada de serviço. O sistema original permanece fora do escopo desta alteração.
