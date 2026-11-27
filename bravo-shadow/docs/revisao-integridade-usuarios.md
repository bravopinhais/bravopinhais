# Revisão de integridade — Gestão de Usuários

**Escopo:** análise estática do módulo de usuários no branch `bravo-shadow`.  
**Status:** proteção transacional de perfil/status implementada de forma isolada no serviço e no repositório PostgreSQL, com testes simulados aprovados. Ainda não está exposta por rota nem validada contra PostgreSQL real. O contrato DDL das tabelas de usuários e auditoria precisa ser formalizado antes do teste de integração.

## 1. Unicidade de e-mail

### Estado encontrado

- `UsuarioInput.normalize_email` remove espaços externos e converte o e-mail para minúsculas.
- `UsuariosService._ensure_email_available` percorre a coleção antes de criar ou atualizar.
- O serviço em memória usa um `RLock` ao redor da sequência verificar-e-gravar em criação e atualização. Isso torna a operação composta atômica dentro de uma instância do serviço.
- O teste concorrente com oito tentativas simultâneas de cadastro do mesmo e-mail verifica que apenas uma criação é aceita e as demais recebem conflito.
- O rascunho SQL cria `usuarios_email_ci_uidx` em `lower(btrim(email))`, protegendo também gravações diretas com espaços externos quando o índice for aplicado.
- `PostgresUsuariosRepository` traduz para HTTP 409 somente a violação SQLSTATE `23505` cuja constraint seja `usuarios_email_ci_uidx`; outras violações de unicidade são propagadas sem serem mascaradas.
- Testes com exceções simuladas cobrem tanto a violação do índice de e-mail quanto a preservação de outras violações únicas.

### Limites remanescentes

- O `RLock` protege somente chamadas que compartilham a mesma instância do serviço; não substitui a restrição única do PostgreSQL em cenários com múltiplos processos ou instâncias.
- O índice PostgreSQL permanece apenas no rascunho SQL. Não foi aplicado em banco.

### Validação

- O GitHub Actions executou com sucesso o workflow `45907681632`, no commit `b7aaee8d3d518c4e02699036cc1d6be9bc493717`.
- A execução cobre os testes adicionados para tratamento seletivo de violações únicas. O teste de concorrência em memória também passou em execução anterior do workflow `45907549214`.
- Isso não equivale a um teste de integração com PostgreSQL real.

## 2. Proteção do último administrador ativo

### Estado encontrado

- O serviço atual permite atualizar `perfil` e `status` por meio do mesmo `UsuarioInput`.
- O serviço permite excluir qualquer usuário encontrado.
- Existe `PostgresUsuariosRepository.update_administrative_state`, que bloqueia a tabela em modo `SHARE ROW EXCLUSIVE`, lê o alvo, conta Admins ativos e rejeita a remoção do último. A operação atualiza perfil/status e chama `append_in_transaction` com a mesma conexão.
- `UsuariosService.update_administrative_state` agora constrói o evento a partir do principal verificado, impede que o ator altere o próprio perfil/status e delega apenas se o repositório implementar a operação transacional. O adaptador em memória retorna 503 sem alterar o usuário.
- Os métodos CRUD genéricos continuam usando unidades de trabalho independentes. A nova operação administrativa é uma exceção explícita e usa uma única unidade de trabalho para bloqueio, contagem, atualização e auditoria.
- O contrato de gestão de usuários e o plano de refatoração propõem separar dados cadastrais de alterações administrativas, mas essa separação ainda não está implementada.

### Risco

Uma verificação simples seguida de atualização não basta: duas operações concorrentes poderiam avaliar o estado antigo e ambas remover privilégios de administradores diferentes, deixando o sistema sem Admin ativo. A mesma proteção precisa abranger rebaixamento, inativação e exclusão.

### Próxima implementação proposta

1. Separar os dados cadastrais das operações privilegiadas de alteração de perfil/status. Os schemas separados existem, mas ainda não estão ligados ao serviço/rotas.
2. **Implementado isoladamente no PostgreSQL:** `update_administrative_state` serializa alterações administrativas com `LOCK TABLE ... IN SHARE ROW EXCLUSIVE MODE`, conta Admins ativos, atualiza o usuário e grava auditoria usando a mesma conexão/UoW.
3. Se a operação reduzir a contagem de Admins ativos abaixo de um, retorna conflito e faz rollback.
4. A autoalteração de perfil/status já é bloqueada no serviço por comparação do e-mail autenticado com o usuário-alvo. Essa validação ainda precisa ser reforçada no limite transacional antes da exposição por rota.
5. O adaptador em memória não possui operação administrativa equivalente e falha fechado com HTTP 503.
6. Testes simulados cobrem sucesso, último Admin, usuário ausente e rollback quando auditoria falha. Falta teste de integração PostgreSQL local descartável porque ainda não há DDL versionado das tabelas `bravo_shadow.usuarios` e `bravo_shadow.audit_events` no Shadow.

## 3. Ordem recomendada antes de ativar a gestão administrativa

1. Aprovar o contrato de gestão de usuários e a regra de cadastro inicial (Ativo, Inativo ou Pendente).
2. Definir formalmente quais perfis podem cadastrar, editar dados, alterar perfil/status, desativar e excluir usuários.
3. Concluído parcialmente: operação atômica no adaptador PostgreSQL, delegação no serviço, bloqueio de autoalteração e falha fechada no adaptador em memória. Falta contrato DDL, integração PostgreSQL real e integração HTTP.
4. Testes unitários simulados adicionados; falta teste de integração PostgreSQL local e teste concorrente real para último Admin.
5. Confirmar a configuração do provedor Google e manter as rotas condicionadas à identidade verificada e às capacidades formalmente aprovadas.

## 4. Limites desta revisão

- Não houve conexão com PostgreSQL ou Supabase.
- O SQL continua sendo rascunho; nenhuma migration foi criada ou aplicada. O índice de e-mail usa `lower(btrim(email))`, mas ainda não foi aplicado em banco.
- A proteção do último Admin está implementada no método transacional PostgreSQL e integrada ao serviço, mas permanece fora das rotas. Os testes atuais do método usam conexão simulada; não foi validada contra PostgreSQL real nem ativada operacionalmente.
- A pasta `docs/sql` não contém, nesta revisão, um DDL versionado das tabelas `bravo_shadow.usuarios` e `bravo_shadow.audit_events`. Os métodos PostgreSQL pressupõem colunas como `updated_at` e `version`; não se deve criar teste de integração com esquema presumido.
- As rotas de usuários possuem dependências de autenticação e capacidades; a matriz de capacidades para Admin/Operador permanece fechada, e a configuração do provedor Google ainda precisa ser confirmada antes de qualquer exposição operacional.
- A proposta não aprova automaticamente a matriz de permissões nem define o estado inicial de novos usuários.
- O workflow de testes citado valida o código coberto por ele, não a implantação, a conexão com banco ou o comportamento em produção.


## Integração PostgreSQL descartável — etapa adicionada

Foi acrescentado `backend/tests/test_usuarios_admin_postgres_integration.py`. O fixture exige `BRAVO_SHADOW_TEST_DATABASE_URL`, aceita somente PostgreSQL em localhost com nome terminado em `_test`, recria o schema isolado `bravo_shadow` a partir dos rascunhos versionados `docs/sql-piloto-financeiro.sql` e `docs/sql-auditoria-rascunho.sql`, e remove o schema ao final.

A cobertura real inclui:
- atualização de perfil/status com evento de auditoria na mesma transação;
- recusa de remoção do último Admin ativo sem alterar usuário nem inserir evento;
- rollback da alteração quando o INSERT de auditoria falha;
- duas remoções concorrentes de Admin, provando que somente uma pode ser confirmada e que permanece um Admin ativo.

**Correção do diagnóstico anterior:** os rascunhos DDL de usuários e auditoria já existem no repositório. Eles definem `bravo_shadow.usuarios` (incluindo `updated_at` e `version`) e `bravo_shadow.audit_events`. O que ainda não existe é uma migration Supabase aplicada/versionada em `supabase/migrations`; os arquivos continuam explicitamente identificados como rascunhos.

A CI já fornece PostgreSQL 16 descartável e a variável de conexão local `BRAVO_SHADOW_TEST_DATABASE_URL`, portanto o novo teste foi ligado ao fluxo normal de backend sem criar credenciais ou acessar banco externo. A validação efetiva depende da execução da CI deste commit.

Nenhum router foi conectado, nenhuma capacidade foi liberada, nenhuma migration foi aplicada e nenhum dado real foi usado.


### Resultado da integração PostgreSQL real

A execução GitHub Actions **45914069701** concluiu com sucesso no commit `2c92bd7864c21a327b0410c29b2a9a16cffb21f6`: **443 testes aprovados**, incluindo os quatro cenários novos com PostgreSQL 16 descartável. O build Docker e o smoke test da API/interface também passaram. Houve um warning de depreciação de dependência de teste, sem falha.

A primeira execução da integração falhou porque o cenário de rollback de auditoria tinha somente um Admin ativo; a proteção do último Admin bloqueou corretamente a operação antes de alcançar o trigger de auditoria. O fixture foi corrigido adicionando um segundo Admin sintético, isolando o teste da regra que ele pretendia exercitar. A execução seguinte passou.
