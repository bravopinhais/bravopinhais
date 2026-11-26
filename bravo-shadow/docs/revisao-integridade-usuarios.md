# Revisão de integridade — Gestão de Usuários

**Escopo:** análise estática do módulo de usuários no branch `bravo-shadow`.  
**Status:** diagnóstico atualizado; correções de unicidade implementadas e cobertas por testes. A proteção do último administrador permanece pendente de definição e implementação.

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
- Não há contagem protegida de administradores ativos, operação transacional de alteração administrativa ou bloqueio para impedir a remoção do último Admin.
- O repositório PostgreSQL atual executa cada operação em sua própria unidade de trabalho; não oferece uma transação de domínio que englobe contagem, validação e alteração.
- O contrato de gestão de usuários e o plano de refatoração propõem separar dados cadastrais de alterações administrativas, mas essa separação ainda não está implementada.

### Risco

Uma verificação simples seguida de atualização não basta: duas operações concorrentes poderiam avaliar o estado antigo e ambas remover privilégios de administradores diferentes, deixando o sistema sem Admin ativo. A mesma proteção precisa abranger rebaixamento, inativação e exclusão.

### Próxima implementação proposta

1. Separar os dados cadastrais das operações privilegiadas de alteração de perfil/status.
2. No PostgreSQL, executar validação e alteração na mesma transação. Serializar operações administrativas com um bloqueio transacional estável (por exemplo, advisory lock dedicado ao domínio de usuários ou uma linha-sentinela bloqueada com `FOR UPDATE`).
3. Após obter o bloqueio, contar os usuários `perfil = 'Admin'` e `status = 'Ativo'`. Se a operação reduzir essa contagem abaixo de um, abortar com conflito de regra de negócio.
4. Aplicar a mesma regra para exclusão e desativação; considerar também impedir que o administrador remova a própria condição de último Admin.
5. No adaptador em memória, executar contagem, validação e mutação dentro de uma única seção crítica.
6. Registrar a alteração administrativa em auditoria na mesma transação PostgreSQL quando a integração de auditoria estiver autorizada e pronta.

## 3. Ordem recomendada antes de ativar a gestão administrativa

1. Aprovar o contrato de gestão de usuários e a regra de cadastro inicial (Ativo, Inativo ou Pendente).
2. Definir formalmente quais perfis podem cadastrar, editar dados, alterar perfil/status, desativar e excluir usuários.
3. Implementar operações atômicas nos adaptadores de memória e PostgreSQL.
4. Criar testes unitários de concorrência e testes de integração PostgreSQL local para último Admin e rollback.
5. Confirmar a configuração do provedor Google e manter as rotas condicionadas à identidade verificada e às capacidades formalmente aprovadas.

## 4. Limites desta revisão

- Não houve conexão com PostgreSQL ou Supabase.
- O SQL continua sendo rascunho; nenhuma migration foi criada ou aplicada. O índice de e-mail usa `lower(btrim(email))`, mas ainda não foi aplicado em banco.
- Nenhuma regra de último administrador foi implementada ou ativada.
- As rotas de usuários possuem dependências de autenticação e capacidades; a matriz de capacidades para Admin/Operador permanece fechada, e a configuração do provedor Google ainda precisa ser confirmada antes de qualquer exposição operacional.
- A proposta não aprova automaticamente a matriz de permissões nem define o estado inicial de novos usuários.
- O workflow de testes citado valida o código coberto por ele, não a implantação, a conexão com banco ou o comportamento em produção.
