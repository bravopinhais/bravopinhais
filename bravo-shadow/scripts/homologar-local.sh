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

command -v supabase >/dev/null 2>&1 || fail "Supabase CLI não instalado."
command -v docker >/dev/null 2>&1 || fail "Docker não instalado."
docker info >/dev/null 2>&1 || fail "Docker não está iniciado ou não está acessível."

printf '\nProjeto: %s\n' "$PROJECT_DIR"
printf 'Escopo: banco local descartável; somente migrations do Shadow.\n'
printf 'CLI: '
supabase --version

printf '\n[1/3] Iniciando serviços locais...\n'
supabase start

printf '\n[2/3] Recriando o banco LOCAL e aplicando migrations...\n'
# Sem --linked: executa contra a stack local iniciada acima.
supabase db reset

printf '\n[3/3] Conferindo histórico de migrations local...\n'
supabase migration list

printf '\nConcluído: comandos locais terminaram sem erro. Isso não valida dados reais,\n'
printf 'não autoriza importação e não publica nem altera a produção.\n'
