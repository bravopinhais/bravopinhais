# Fundação de auditoria — Bravo Shadow

## Status

**Implementação isolada para desenvolvimento/testes.** O módulo `backend/app/core/audit.py` define eventos imutáveis, contrato `AuditSink` e adaptador em memória append-only. Ele não está conectado à aplicação, aos serviços, aos routers ou ao banco.

## Estrutura criada

- `AuditEvent`: evento imutável com identificador técnico, sujeito do ator, ação, tipo/ID da entidade, resultado, request ID opcional e instante com fuso horário.
- `AuditSink`: protocolo mínimo para um destino de auditoria.
- `InMemoryAuditSink`: adaptador de testes que só acrescenta eventos e devolve snapshots em tupla.
- `backend/tests/test_audit.py`: testes escritos para imutabilidade, timestamp com fuso, validação de campos, resultados permitidos e comportamento append-only.

## Dados que podem entrar no evento

- `actor_subject` deve ser o `sub` da identidade Google já validada pelo backend, nunca um valor recebido diretamente do navegador.
- `action` deve ser uma capacidade/ação canônica, como `financeiro:create`.
- `entity_type` deve ser um nome técnico de entidade.
- `entity_id` deve ser um identificador interno não sensível.
- `outcome` aceita somente `success`, `denied` ou `failure`.
- `request_id` pode correlacionar a operação sem armazenar corpo da requisição.

Não registrar e-mail, nome, CPF, telefone, endereço, conteúdo de documentos, token Google, cabeçalho Authorization, senha, hash, segredo, payload completo ou valores financeiros. O módulo não oferece campo genérico de metadata justamente para reduzir o risco de captura acidental.

## Limitações conhecidas

- O adaptador em memória perde eventos ao reiniciar e não compartilha eventos entre processos/workers.
- Não há persistência PostgreSQL, retenção, exportação, consulta HTTP, autenticação de consulta ou proteção contra adulteração por quem controla o processo.
- `frozen=True` protege o objeto no uso normal da aplicação; não equivale a armazenamento inviolável ou trilha criptograficamente verificável.
- A existência do contrato não prova que uma operação foi auditada. Os serviços ainda não chamam o sink.
- Os testes foram escritos, mas não executados nesta etapa.

## Próxima etapa antes de integração

1. Definir tabela PostgreSQL append-only e índices para instante, ator, ação e entidade.
2. Definir privilégios do banco: papel de escrita sem UPDATE/DELETE; leitura separada e restrita.
3. Definir retenção, backup, monitoramento de falha e política de acesso aos eventos.
4. Garantir que a falha ao registrar operações críticas resulte em rollback/negação conforme a criticidade, sem mascarar a falha de auditoria.
5. Injetar o sink nos serviços e registrar somente após identidade confiável e autorização resolvidas.
6. Testar que tokens e dados pessoais nunca aparecem nos eventos e que operações críticas geram eventos em sucesso e negação.

## Segurança e escopo preservados

Nenhuma rota foi criada ou alterada; nenhum endpoint de consulta foi exposto; nenhum evento de usuário real foi registrado; nenhuma migration ou tabela foi criada; nenhum banco foi conectado. A autenticação Google, a matriz de permissões e o provisionamento do primeiro Admin continuam como etapas separadas e pendentes. O sistema original permanece fora do escopo.