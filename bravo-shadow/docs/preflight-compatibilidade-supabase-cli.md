# Preflight de compatibilidade com Supabase CLI

## Escopo

A pasta `supabase/` deste diretório é a raiz do projeto CLI do Bravo Shadow.
As seis migrations usam o formato de versão numérica de 14 dígitos seguido de
`_` e um identificador: `YYYYMMDDHHMMSS_nome.sql`. A ordenação lexical
corresponde à ordem de aplicação do CLI.

O `config.toml` contém apenas um identificador local. Não há `project_id`
remoto, bloco `[remotes.*]`, credenciais, senha de banco ou configuração de
deploy. A configuração não conecta nem provisiona banco por si só.

## Checagens estáticas concluídas

- Seis arquivos SQL em `supabase/migrations/`, com versões únicas e ordem
  determinística.
- Configuração CLI presente na raiz esperada.
- Nenhum vínculo remoto declarado no TOML.
- Os esquemas e tabelas sensíveis continuam sem GRANT para roles comuns e com
  RLS habilitado conforme os DDLs atuais.
- A detecção estática de GRANT verifica início de instrução SQL (não palavras
  em comentários); isso é apenas uma verificação textual, não um parser SQL.

## Limites ainda não verificados

Não foi executado `supabase --version`, `supabase --help`, parser TOML,
Docker, PostgreSQL, `supabase start`, `supabase db reset`,
`supabase migration list` ou qualquer SQL. Portanto, a compatibilidade
operacional com a versão instalada do CLI permanece **não verificada**.

Também permanecem pendentes a validação de sintaxe pelo PostgreSQL, a
existência das roles Supabase esperadas (`anon`, `authenticated`,
`service_role`), as permissões efetivas, o comportamento dos triggers e a
ordem de dependências em um banco descartável.

## Procedimento futuro — exige autorização explícita

1. Confirmar a versão e consultar os comandos disponíveis:
   `supabase --version`, `supabase --help`, `supabase db --help`.
2. Confirmar que o terminal está no diretório `bravo-shadow/` e que o
   `supabase/config.toml` local é o único projeto configurado.
3. Confirmar Docker e recursos locais disponíveis.
4. Somente após autorização expressa para criar/iniciar um banco descartável,
   iniciar a stack local e aplicar migrations nela.
5. Inspecionar a lista de migrations locais e executar verificações de schema,
   RLS, constraints, triggers, índices e FKs.
6. Registrar falhas e corrigir os arquivos antes de qualquer nova tentativa.

**Não executar** `supabase link`, `supabase db push`,
`supabase db reset --linked`, nem fornecer qualquer credencial remota.
Não importar dados reais, não criar projeto hospedado e não publicar Shadow.
