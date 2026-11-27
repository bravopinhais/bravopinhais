# Preflight de compatibilidade com Supabase CLI

## Escopo

A pasta `supabase/` deste diretório é a raiz do projeto CLI do Bravo Shadow.
As seis migrations usam o formato de versão numérica de 14 dígitos seguido de
`_` e um identificador: `YYYYMMDDHHMMSS_nome.sql`. A ordenação lexical
corresponde à ordem de aplicação do CLI.

O `config.toml` contém apenas o identificador local
`bravo-shadow-local`. Não há vínculo remoto, credenciais, senha de banco ou
configuração de deploy. A configuração não conecta nem provisiona banco por si só.

## Checagens estáticas registradas

- Seis arquivos SQL em `supabase/migrations/`, com versões únicas e ordem
  determinística.
- Configuração CLI presente na raiz esperada.
- Nenhum vínculo remoto declarado no TOML.
- As verificações estáticas existentes inspecionam os DDLs e os contratos de
  segurança; não substituem a inspeção do catálogo PostgreSQL.
- A detecção textual de GRANT verifica início de instrução SQL; não é um parser SQL.

## Homologação local autorizada

Foi concedida autorização expressa para criar e iniciar **somente um banco
local descartável**, destinado à homologação das migrations do Shadow. Essa
autorização não inclui projeto hospedado, conexão remota, dados reais,
importação, publicação, cutover ou alteração da produção.

Foi adicionado o script protegido
`scripts/homologar-local.sh`. A partir de um clone da branch
`bravo-shadow`, execute na pasta `bravo-shadow/`:

```bash
bash scripts/homologar-local.sh
```

O script:
1. exige que a branch Git atual seja exatamente `bravo-shadow`;
2. exige a configuração local `bravo-shadow-local`;
3. interrompe se detectar marcador de projeto Supabase vinculado ou bloco de remoto;
4. exige Supabase CLI e Docker disponíveis e Docker iniciado;
5. inicia a stack local com `supabase start`;
6. recria **apenas o banco local** com `supabase db reset --local`;
7. consulta o histórico com `supabase migration list --local`.

O script não instala ferramentas, não executa `supabase link`,
`supabase db push`, não usa credenciais remotas e não importa dados. Se uma
verificação de segurança falhar, ele para sem tentar corrigir vínculo ou
configuração automaticamente.

## Estado de execução

O ambiente de execução anteriormente disponível não tinha Docker, Supabase CLI
ou PostgreSQL/psql. Portanto, **nenhuma migration foi executada em PostgreSQL**
e a compatibilidade operacional permanece não verificada. O script foi
preparado para executar a etapa assim que houver um terminal com Docker e
Supabase CLI instalados; sua criação não significa que a homologação passou.

### Auditoria read-only do catálogo

Foi adicionado `scripts/validar-catalogo-local.sql`. Depois que o reset local
terminar, obtenha a URL do banco local pelo comando `supabase status` e execute
o arquivo com o cliente PostgreSQL, usando somente a URL local exibida pela
stack local:

```bash
psql "$LOCAL_DB_URL" -v ON_ERROR_STOP=1 -f scripts/validar-catalogo-local.sql
```

`LOCAL_DB_URL` deve ser definida manualmente com a URL local apresentada por
`supabase status`; não use URL de projeto hospedado. O SQL não consulta linhas
de negócio nem altera dados ou schema. Ele interrompe com erro se encontrar:
tabelas esperadas ausentes, RLS desabilitado, policies inesperadas, privilégios
de tabela/schema para `anon`, `authenticated` ou `service_role`, ausência de
FORCE RLS na auditoria, triggers append-only ausentes/desabilitados ou
constraints que impedem autorização de escrita na aprovação pré-importação.

A auditoria é uma verificação de catálogo direcionada aos 27 objetos/tabelas
definidos nas migrations atuais; não substitui revisão manual de cada FK,
índice, tipo, trigger ou comportamento da aplicação.

Depois da execução, ainda será necessário revisar FKs, índices, constraints,
triggers e resultados de cada migration, registrar falhas e corrigir os
arquivos. Os testes automatizados não foram executados.

## Proibições permanentes deste fluxo

Não executar `supabase link`, `supabase db push`,
`supabase db reset --linked`, nem fornecer credencial remota.
Não importar dados reais, não criar projeto hospedado e não publicar Shadow.
