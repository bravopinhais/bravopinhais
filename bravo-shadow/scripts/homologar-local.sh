#!/usr/bin/env bash
set -Eeuo pipefail

# Homologação exclusivamente local do Bravo Shadow.
# Não instala ferramentas, não cria projeto hospedado e não acessa produção.

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
cd "$PROJECT_DIR"

fail() {
  printf 'BLOQUEADO: %s\n' "$1" >&2
  exit 1
}

command -v git >/dev/null 2>&1 || fail "Git não instalado."
CURRENT_BRANCH="$(git branch --show-current 2>/dev/null || true)"
[[ "$CURRENT_BRANCH" == "bravo-shadow" ]] || fail "Branch atual é '$CURRENT_BRANCH'; execute somente na branch bravo-shadow."

[[ -f "supabase/config.toml" ]] || fail "supabase/config.toml não encontrado."
grep -Eq '^[[:space:]]*project_id[[:space:]]*=[[:space:]]*"bravo-shadow-local"[[:space:]]*$' supabase/config.toml \
  || fail "A configuração não corresponde ao projeto local bravo-shadow-local."

# Um projeto previamente vinculado é motivo para parar, nunca para tentar
# desvincular ou adivinhar o destino.
[[ ! -e "supabase/.temp/project-ref" ]] || fail "Foi encontrado vínculo Supabase em supabase/.temp/project-ref. Não execute neste estado."
[[ ! -e ".supabase/.temp/project-ref" ]] || fail "Foi encontrado vínculo Supabase em .supabase/.temp/project-ref. Não execute neste estado."
if grep -Eq '^[[:space:]]*\[remotes\.' supabase/config.toml; then
  fail "A configuração contém bloco de remoto."
fi

# Não permitir que credenciais/URLs remotas herdadas do shell confundam
# uma futura alteração do script ou da CLI. Os nomes são verificados sem
# imprimir seus valores.
for variable in \
  SUPABASE_ACCESS_TOKEN \
  SUPABASE_URL \
  SUPABASE_DB_URL \
  SUPABASE_DB_PASSWORD \
  SUPABASE_SERVICE_ROLE_KEY \
  BRAVO_DATABASE_URL \
  BRAVO_SHADOW_TEST_DATABASE_URL; do
  if [[ -n "${!variable-}" ]]; then
    fail "A variável de ambiente $variable está definida. Limpe o ambiente remoto antes de continuar."
  fi
done

command -v supabase >/dev/null 2>&1 || fail "Supabase CLI não instalado."
command -v docker >/dev/null 2>&1 || fail "Docker não instalado."
docker info >/dev/null 2>&1 || fail "Docker não está iniciado ou não está acessível."

printf '\nProjeto: %s\n' "$PROJECT_DIR"
printf 'Branch: %s\n' "$CURRENT_BRANCH"
printf 'Escopo: banco local descartável; somente migrations do Shadow.\n'
printf 'CLI: '
supabase --version

printf '\n[1/3] Iniciando serviços locais...\n'
supabase start

printf '\n[2/3] Recriando o banco LOCAL e aplicando migrations...\n'
# --local fixa explicitamente o destino; nunca usar --linked.
supabase db reset --local

printf '\n[3/3] Conferindo histórico de migrations local...\n'
supabase migration list --local

printf '\nConcluído: comandos locais terminaram sem erro. Isso não valida dados reais,\n'
printf 'não autoriza importação e não publica nem altera a produção.\n'
