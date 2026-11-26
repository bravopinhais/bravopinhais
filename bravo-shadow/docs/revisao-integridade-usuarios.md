# Revisão de integridade — Gestão de Usuários

**Escopo:** análise estática do módulo de usuários no branch `bravo-shadow`.  
**Status:** diagnóstico e proposta; nenhuma regra funcional foi alterada e nenhum teste foi executado.

## 1. Unicidade de e-mail

### Estado encontrado

- `UsuarioInput.normalize_email` remove espaços externos e converte o e-mail para minúsculas.
- `UsuariosService._ensure_email_available` percorre a coleção antes de criar ou atualizar.
- O repositório em memória protege individualmente `list` e `add` com `RLock`, mas a sequência verificar-e-gravar não é uma única operação atômica.
- O rascunho SQL cria `usuarios_email_ci_uidx` em `lower(email)`, que impede duplicidade concorrente no PostgreSQL para e-mails normalizados.
- `PostgresUsuariosRepository` traduz qualquer erro SQLSTATE `23505` para conflito de e-mail. Isso pode mascarar uma violação de outra restrição única que venha a ser adicionada.

### Risco

No backend em memória, duas requisições concorrentes podem consultar a coleção antes de qualquer uma gravar e ambas concluir o cadastro. O `RLock` atual não protege a operação composta. Em PostgreSQL, o índice único fecha a corrida, mas a tradução de erro deve identificar a restrição violada.

### Correção proposta

1. Acrescentar ao contrato do repositório de usuários uma operação atômica de criação/alteração que valide e grave o e-mail sob o mesmo bloqueio no adaptador em memória.
2. No PostgreSQL, manter a restrição única como autoridade final; normalizar no serviço/schema e considerar índice em `lower(btrim(email))` ou uma restrição equivalente para também proteger gravações diretas com espaços externos.
3. Na captura de `23505`, verificar o nome da constraint/índice (por exemplo, `usuarios_email_ci_uidx`) antes de retornar HTTP 409 de e-mail duplicado. Repropagar violações de outras constraints corretamente.
4. Testar duas criações concorrentes com o mesmo e-mail em variantes de caixa e espaços, além da atualização que mantém o próprio e-mail.

## 2. Proteção do último administrador ativo

### Estado encontrado

- O serviço atual permite atualizar `perfil` e `status` por meio do mesmo `UsuarioInput`.
- O serviço permite excluir qualquer usuário encontrado.
- Não há contagem protegida de administradores ativos, operação transacional de alteração administrativa ou bloqueio para impedir a remoção do último Admin.
- O repositório PostgreSQL atual executa cada operação em sua própria unidade de trabalho; não oferece uma transação de domínio que englobe contagem, validação e alteração.
- O contrato de gestão de usuários e o plano de refatoração já propõem separar dados cadastrais de alterações administrativas, mas não implementam essa proteção.

### Risco

Uma verificação simples seguida de atualização não basta: duas operações concorrentes poderiam avaliar o estado antigo e ambas remover privilégios de administradores diferentes, deixando o sistema sem Admin ativo. A mesma proteção precisa abranger rebaixamento, inativação e exclusão.

### Correção proposta

1. Concentrar mudanças de perfil/status e desativação em operações específicas do serviço/repositório; não permitir que o endpoint cadastral altere esses campos.
2. No PostgreSQL, executar a validação e a alteração na mesma transação. Serializar operações administrativas com um bloqueio transacional estável (por exemplo, advisory lock dedicado ao domínio de usuários ou uma linha-sentinela bloqueada com `FOR UPDATE`).
3. Após obter o bloqueio, contar os usuários `perfil = 'Admin'` e `status = 'Ativo'`. Se a operação reduzir essa contagem abaixo de um, abortar com conflito de regra de negócio.
4. Aplicar a mesma regra para exclusão e desativação; considerar também impedir que o administrador remova a própria condição de último Admin.
5. No adaptador em memória, executar contagem, validação e mutação dentro de uma única seção crítica.
6. Registrar a alteração administrativa em auditoria na mesma transação PostgreSQL quando a integração de auditoria estiver autorizada e pronta.

## 3. Ordem recomendada antes de implementar

1. Aprovar o contrato de gestão de usuários e a regra de cadastro inicial (Ativo, Inativo ou Pendente).
2. Definir formalmente quais perfis podem cadastrar, editar dados, alterar perfil/status, desativar e excluir usuários.
3. Implementar operações atômicas nos adaptadores de memória e PostgreSQL.
4. Criar testes unitários de concorrência e testes de integração PostgreSQL local para duplicidade, último Admin e rollback.
5. Proteger as rotas com identidade Google verificada e capacidades aprovadas antes de expor qualquer operação administrativa.

## 4. Limites desta revisão

- Não houve conexão com PostgreSQL ou Supabase.
- O SQL continua sendo rascunho; nenhuma migration foi criada ou aplicada.
- Nenhuma rota, schema, serviço, tabela, permissão ou tela foi alterada.
- As rotas de usuários continuam sem autenticação/autorização; não devem ser expostas publicamente.
- A proposta não aprova automaticamente a matriz de permissões nem define o estado inicial de novos usuários.
- Os testes existentes continuam sem evidência de execução.
