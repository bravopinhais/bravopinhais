# Plano do piloto de auditoria — Acerto de Estoque

## Decisão técnica

O primeiro candidato para integração é a criação de movimentações em **Acerto de Estoque**. O repositório PostgreSQL `PostgresAcertosEstoqueRepository.register_movement` já executa, na mesma unidade de trabalho:

1. bloqueio do produto com `SELECT ... FOR UPDATE`;
2. validação do saldo;
3. atualização da quantidade;
4. inserção do movimento;
5. commit ou rollback pela unidade de trabalho.

A auditoria deve ser inserida nessa mesma conexão, antes do commit, usando `PostgresAuditSink.append_in_transaction(connection, event)`. Assim, não haverá movimento confirmado sem evento de auditoria, nem evento de sucesso confirmado sem movimento.

## Pré-condições obrigatórias

A integração não deve ser ativada até que todos os itens abaixo sejam atendidos:

- PostgreSQL local descartável iniciado e migration da auditoria aplicada por Supabase CLI.
- Role da API validada com INSERT na tabela de auditoria e sem UPDATE, DELETE, TRUNCATE, DDL, ownership ou BYPASSRLS.
- Testes reais de RLS e privilégios aprovados.
- Rota POST de Acerto de Estoque protegida por autenticação Google validada no servidor.
- Capacidade `acertos_estoque:create` aprovada na matriz de permissões e aplicada à rota.
- Identidade `actor_subject` extraída exclusivamente do principal autenticado, nunca do corpo da requisição.
- Política de falha da auditoria definida: se o INSERT falhar, a movimentação inteira deve sofrer rollback.
- Testes de integração cobrindo sucesso e falha do INSERT na mesma transação.

## Alteração prevista quando as pré-condições forem aprovadas

1. Injetar o sink de auditoria no serviço/repositório de movimentação, sem singleton global.
2. Propagar o principal autenticado até a operação de criação sem aceitar identidade enviada pelo cliente.
3. Construir o evento com ação canônica `acertos_estoque:create`, tipo de entidade `acertos_estoque`, ID técnico do movimento, resultado `success` e request ID confiável quando disponível.
4. Dentro de `register_movement`, após atualizar saldo e inserir o movimento, executar o INSERT de auditoria usando a mesma conexão.
5. Deixar o `PostgresUnitOfWork` confirmar tudo junto. Qualquer exceção deve reverter saldo, movimento e auditoria.
6. Não gravar motivo livre, dados de produto, quantidade, valores, payload ou dados pessoais no evento.
7. Manter imutabilidade do movimento; correções continuam sendo novos movimentos compensatórios.

## Casos de teste obrigatórios

- Movimento válido: saldo, movimento e evento confirmados.
- INSERT de auditoria falha: saldo e movimento revertidos.
- Falha ao atualizar saldo: nenhum movimento ou evento confirmado.
- Saldo insuficiente: operação negada sem evento de sucesso.
- Principal ausente ou inválido: rota bloqueada antes da operação.
- Perfil sem capacidade: resposta 403 e nenhum movimento.
- Tentativa de UPDATE/DELETE do evento pela role writer: negada pelo PostgreSQL.
- Confirmar que writer não consegue consultar eventos, se leitura permanecer separada.

Eventos de negação ocorridos antes da transação de negócio exigem política separada e não devem ser registrados como sucesso. A trilha não deve capturar conteúdo da requisição.

## Estado atual

Este documento é apenas o plano do piloto. Nenhum serviço, repositório ou router foi alterado para integrar auditoria. A rota de Acerto de Estoque permanece sem proteção e não deve ser exposta publicamente. A matriz de permissões continua pendente de aprovação. Nenhuma migration ou banco local foi executado neste ambiente.

O adaptador transacional está disponível em `backend/app/core/postgres_audit.py`; seus testes unitários usam conexão simulada e ainda não foram executados. A integração real depende das pré-condições acima.
