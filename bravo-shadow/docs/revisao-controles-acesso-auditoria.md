# Revisão de controles de acesso — auditoria PostgreSQL

**Data:** 27/11/2026  
**Escopo:** revisão estática do rascunho `docs/sql-auditoria-rascunho.sql`, do adaptador Python e dos contratos de autorização.  
**Natureza:** análise documental; não executa SQL, não conecta banco e não altera privilégios.

## Resultado

**Apto para continuar em ambiente local descartável, mas não apto para produção ou conexão operacional.**

O rascunho aplica `ENABLE ROW LEVEL SECURITY` e `FORCE ROW LEVEL SECURITY` à tabela proposta e revoga privilégios de `PUBLIC`, `anon`, `authenticated` e `service_role`. Não há concessão para uma role writer ou reader dedicada, nem policies de leitura. Portanto, o desenho atual é deliberadamente fechado: ainda não permite que a API grave nem que um operador consulte a auditoria.

## Matriz de acesso revisada

| Identidade | Acesso pretendido | Estado atual |
|---|---|---|
| Owner/migration | DDL e migrations fora da API | Conceito documentado; role não criada |
| Writer/API | Somente INSERT | Conceito documentado; sem role, grant ou membership |
| Reader/auditoria | SELECT restrito | Conceito documentado; sem role, grant, policy ou rota |
| PUBLIC / anon / authenticated / service_role | Nenhum acesso concedido pelo rascunho | REVOKE ALL explícito no SQL proposto; não aplicado |

## Controles que devem ser provados localmente

1. Confirmar que nenhuma role da API tem `SUPERUSER`, `BYPASSRLS`, ownership da tabela ou privilégios herdados que contornem RLS.
2. Confirmar memberships efetivas e privilégios herdados, não apenas grants diretos.
3. Confirmar que writer pode executar INSERT e não pode SELECT, UPDATE, DELETE, TRUNCATE ou DDL.
4. Confirmar que reader pode executar somente SELECT conforme escopo aprovado e não pode inserir, editar ou apagar.
5. Confirmar que `PUBLIC`, `anon`, `authenticated` e `service_role` não conseguem ler nem modificar a tabela.
6. Confirmar que owner/migration não é usado pela aplicação e que credenciais administrativas não são expostas ao frontend.
7. Confirmar que nenhuma policy permissiva (`USING (true)` / `WITH CHECK (true)`) foi introduzida para contornar o bloqueio.
8. Testar os privilégios com `SET ROLE` e consultas efetivas no PostgreSQL local descartável; registrar os resultados sem dados reais.

## Observações técnicas

- RLS não substitui privilégios SQL: os grants devem ser mínimos e testados em conjunto com as policies.
- `FORCE ROW LEVEL SECURITY` sujeita o owner às policies em operações normais, mas não neutraliza superusers ou roles com `BYPASSRLS`.
- `REVOKE` no rascunho é apenas texto versionado; não altera qualquer banco até uma migration ser criada e aplicada.
- O adaptador `PostgresAuditSink` oferece somente INSERT no nível da aplicação. Isso não é uma barreira de segurança suficiente se a credencial PostgreSQL possuir privilégios maiores.
- A consulta de auditoria ainda não possui endpoint nem capacidade concedida. Não criar uma rota de leitura antes de aprovar o modelo de acesso.
- A matriz `ROLE_CAPABILITIES` continua vazia para Admin e Operador. Esta revisão não recomenda nem concede permissões funcionais.

## Pendências antes de qualquer integração

- Definir nomes reais das roles e seus memberships na stack local.
- Definir o escopo de leitura e a capacidade específica para consulta de auditoria.
- Definir retenção, backup, restauração e monitoramento.
- Gerar migration por ferramenta apropriada somente após revisão do desenho.
- Aplicar e testar apenas em PostgreSQL local descartável, com dados sintéticos.
- Fazer revisão independente dos resultados e obter autorização explícita antes de qualquer ambiente compartilhado ou produção.

## Limites desta revisão

Nenhuma migration foi criada ou aplicada. Nenhuma role, policy, grant, membership, segredo ou variável de ambiente foi criada ou alterada. Nenhum banco foi acessado. O login Google, a interface original, a matriz de permissões e o fluxo de produção permanecem inalterados.

## Evidência automatizada complementar — 27/11/2026

O commit `96e4b47152b0167b2ac9bf056cff103c6b158767` acrescentou dois testes de contrato para o rascunho de auditoria: confirmação de RLS habilitado/forçado e revogações explícitas, além da ausência de GRANT e policies no texto SQL.

A execução GitHub Actions `45983529674` concluiu os trabalhos Backend e Docker com sucesso. O backend reportou **562 testes aprovados, 1 aviso de depreciação e nenhuma falha**. O trabalho Docker concluiu construção, inicialização do contêiner e smoke test de interface/API.

Esta evidência valida os contratos automatizados do repositório e o comportamento do contêiner de demonstração. **Não** comprova privilégios efetivos em um banco compartilhado, não aplica o rascunho SQL e não autoriza integração operacional ou produção. A revisão de roles, memberships, grants e policies ainda depende de execução controlada em PostgreSQL local descartável.
