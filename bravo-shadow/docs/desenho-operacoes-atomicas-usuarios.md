# Desenho das operações atômicas — Gestão de Usuários

**Status:** desenho técnico para a próxima implementação; não implementado.  
**Escopo:** somente sistema sombra. Nenhuma rota, regra, tabela, dado ou permissão foi alterada. O router atual de usuários já exige autenticação e capacidades `usuarios:*`; a matriz de Admin/Operador permanece fechada e o provedor Google ainda depende de configuração validada.

## Objetivo

Fechar as duas condições de corrida identificadas na revisão de integridade:

1. impedir que duas requisições criem ou atribuam o mesmo e-mail;
2. impedir que operações concorrentes deixem o sistema sem ao menos um Admin ativo.

A camada de serviço não deve tentar garantir atomicidade com uma sequência `list/get` seguida de `add/replace/delete`. A garantia deve pertencer ao repositório especializado de usuários.

## 1. Contrato especializado do repositório

Criar um contrato específico para usuários, sem ampliar o contrato genérico de todas as coleções. Operações conceituais:

- `create_unique_email(user)`: grava o cadastro e garante unicidade no mesmo limite atômico;
- `update_profile_data(user_id, changes)`: atualiza somente campos cadastrais permitidos, com política explícita para e-mail;
- `update_administration(user_id, profile?, status?, actor_id)`: altera perfil/status com proteção contextual;
- `deactivate(user_id, actor_id)`: desativação lógica protegida;
- `list/get`: leitura conforme capacidade, quando as rotas forem protegidas.

Não manter métodos genéricos de escrita administrativa que permitam contornar essas operações. A migração deve remover o uso de `UsuarioInput` combinado para criação e atualização.

## 2. Adaptador em memória

Implementar repositório dedicado com um único `RLock` por instância. Cada operação composta deve manter o bloqueio desde a leitura/validação até a gravação:

### E-mail
- Normalizar com `strip().lower()` antes de entrar no repositório.
- Dentro do lock, procurar outro usuário com o mesmo e-mail normalizado.
- Se existir, retornar conflito de domínio; caso contrário, inserir/substituir antes de liberar o lock.
- Na atualização, excluir da comparação somente o próprio `user_id`.

### Último Admin
- Dentro do mesmo lock, localizar o usuário-alvo e calcular a contagem atual de Admins ativos.
- Calcular o estado resultante da operação.
- Se a operação transformar o alvo de Admin ativo em não-Admin ou inativo e a contagem atual for 1, rejeitar sem mutar a coleção.
- Executar a mutação antes de liberar o lock.
- Aplicar o mesmo controle a desativação. Exclusão física não deve ser implementada nesta etapa; a proposta é desativação lógica.

O adaptador em memória serve para desenvolvimento e testes unitários de uma única instância. Não oferece coordenação entre múltiplos processos/workers e não pode ser considerado armazenamento de produção.

## 3. Adaptador PostgreSQL

Todas as operações compostas devem abrir uma única `PostgresUnitOfWork` e usar sua conexão durante validação e escrita.

### E-mail
- Manter índice único case-insensitive; ajustar o rascunho SQL para `lower(btrim(email))` ou equivalente, evitando divergência com a normalização do serviço.
- Tratar `23505` como HTTP 409 somente quando `constraint_name` corresponder ao índice/constraint de e-mail.
- Outras violações únicas devem ser propagadas ou traduzidas de acordo com sua própria regra, nunca rotuladas como e-mail duplicado.

### Último Admin
- Adquirir bloqueio transacional de domínio antes de contar ou alterar administradores. Opção proposta: `SELECT pg_advisory_xact_lock(<chave bigint fixa e documentada>)`.
- O bloqueio deve ser adquirido em toda operação que possa reduzir o conjunto de Admins ativos: alteração de perfil, alteração de status e desativação.
- Com o bloqueio adquirido, executar a consulta de contagem e a escrita na mesma conexão/transação.
- Se a operação reduzir o total de Admins ativos abaixo de um, lançar conflito e permitir que a unidade de trabalho faça rollback.
- Usar parâmetros SQL para todos os valores; a chave do advisory lock é constante do código, não fornecida pelo cliente.
- Não confiar em `SELECT ... FOR UPDATE` apenas sobre a linha-alvo: operações em alvos diferentes ainda poderiam concorrer. O bloqueio deve serializar o conjunto administrativo.
- Definir isolamento e comportamento de retry após teste local; não implementar retry cego para deadlocks.

### Exclusão e retenção
- Não expor exclusão física nesta refatoração.
- Preferir `status = 'Inativo'` e preservar o registro para histórico/auditoria.
- Qualquer futura exclusão física exige política de retenção aprovada e a mesma trava de último Admin.

## 4. Identidade e auditoria

- `actor_id` deve vir do principal criado após validação do Google ID token; nunca do corpo ou query string.
- A checagem de autoalteração de perfil/status deve ocorrer no serviço, comparando o ator autenticado com o usuário-alvo.
- A capacidade necessária deve ser verificada antes de chamar o método administrativo do repositório. O router já possui dependências de autenticação e capacidades; manter a matriz fechada até aprovação formal.
- Quando a integração de auditoria estiver pronta, gravar evento na mesma transação da alteração. Falha ao registrar auditoria deve cancelar a alteração.
- Não gravar e-mail, nome, perfil antigo/novo, status antigo/novo ou payload no evento; usar somente ator opaco, ação, tipo/ID da entidade, resultado e request ID conforme o contrato de auditoria existente.

## 5. Mapeamento de conflitos

| Situação | Resultado esperado |
|---|---|
| E-mail já utilizado | HTTP 409, sem gravar |
| Usuário-alvo inexistente | HTTP 404 |
| Tentativa de remover o último Admin ativo | HTTP 409, sem alterar |
| Ator tenta alterar o próprio perfil/status | HTTP 403 |
| Capacidade ausente | HTTP 403 antes da mutação |
| Falha de auditoria | rollback integral |
| Violação de constraint não relacionada ao e-mail | erro próprio, sem mensagem enganosa |

Os códigos HTTP finais devem seguir o padrão de exceções do projeto quando a implementação for feita.

## 6. Testes de aceitação necessários

### Memória
1. Duas threads tentam criar e-mails iguais com caixa diferente: exatamente uma vence.
2. Duas threads tentam atribuir o mesmo e-mail a usuários diferentes: exatamente uma vence.
3. Atualizar o próprio cadastro mantendo o mesmo e-mail é permitido.
4. Tentar rebaixar/desativar o único Admin é rejeitado e o registro permanece igual.
5. Com dois Admins ativos, rebaixar um é permitido; tentar rebaixar o último depois é rejeitado.
6. Duas operações concorrentes em Admins distintos não conseguem deixar zero Admin ativo.
7. Desativação preserva o registro.

### PostgreSQL local descartável
1. Repetir cenários de e-mail concorrente com duas conexões independentes.
2. Repetir cenário do último Admin com duas conexões e alvos diferentes.
3. Verificar que bloqueio transacional é liberado no commit e rollback.
4. Simular falha após validação e confirmar rollback.
5. Confirmar que constraint de outra natureza não retorna mensagem de e-mail duplicado.
6. Executar todos os cenários exclusivamente na stack local; sem projeto hospedado, sem `--remote`.

## 7. Dependências e bloqueios antes da implementação

- Aprovar estado inicial de novos usuários (Ativo, Inativo ou Pendente).
- Aprovar matriz de capacidades e quem pode cadastrar/editar/administrar/desativar.
- Confirmar a decisão de desativação lógica como padrão.
- Concluir contrato de auditoria transacional.
- Preparar PostgreSQL local descartável e migrations revisadas.

Até essas decisões e pré-requisitos estarem resolvidos, manter este documento como desenho, sem alterar o serviço, repositórios ou rotas. Não conectar o sistema sombra a dados reais nem expor rotas sem autenticação e autorização completas.
