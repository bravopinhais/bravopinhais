# Revisão de integração e arquitetura — Bravo Shadow

## Estado da revisão — 26/11/2026

Revisão estática da branch `bravo-shadow`. Os 15 routers foram inspecionados e todos resolvem seus serviços por `request.app.state.services`; nenhum dos routers inspecionados importa diretamente um singleton de serviço. A composição de serviços está concentrada em `build_storage_services()`, chamada por `create_app()`.

Esta verificação é de código-fonte. Não representa teste de execução, teste de browser, teste de banco ou homologação funcional. O CI da etapa mais recente ainda deve concluir antes de considerar os novos módulos validados.

## Arquitetura atual

- Uma aplicação FastAPI integrada, com 15 módulos/recursos e API versionada em `/api/v1`.
- Serviços e repositórios construídos por instância de aplicação e expostos em `app.state.services`.
- Repositório em memória como padrão seguro; adequado a desenvolvimento/testes, não a produção, multi-worker ou persistência após reinício.
- Adaptadores PostgreSQL existem apenas para Formas Monetárias, Plano de Contas e Financeiro.
- O frontend sombra pode ser servido pelo processo FastAPI, mas a integração completa de todas as telas com as APIs ainda não foi homologada.
- CORS permanece fechado até definição de allowlist.
- Nenhuma conexão com banco de produção foi configurada ou executada.

## Matriz dos 15 módulos

| Módulo | Serviço por aplicação | Persistência PostgreSQL | Observações |
|---|---|---|---|
| Dashboard | Não possui serviço próprio | Não | Indicadores atuais são demonstrativos; falta endpoint agregado |
| Condomínio | Sim | Não | Cadastro único em memória; atualização parcial preserva campos não enviados |
| Conselho | Sim | Não | CRUD em memória |
| Plano de Contas | Sim | Sim, adaptador existente | Verifica referências financeiras; restrição final deve ser garantida no banco |
| Contas a Pagar/Receber | Sim | Sim, adaptador existente | Usa `planoContaId`; vínculo opcional no contrato atual |
| Formas Monetárias | Sim | Sim, adaptador existente | Piloto de persistência |
| Contas Bancárias/Caixa | Sim | Não | Saldo informado/manual, não equivale a conciliação bancária |
| Moradores/Unidades | Sim | Não | CRUD, filtros e importação em lote em memória |
| Fornecedores | Sim | Não | CRUD em memória; vínculo financeiro não confirmado |
| Empregados | Sim | Não | CRUD em memória; dados pessoais exigem controles de privacidade |
| Pastas/Categorias | Sim | Não | Documentos podem apontar para categoria por ID; exclusão referenciada é bloqueada |
| Estoque/Inventário | Sim | Não | CRUD em memória |
| Acerto de Estoque | Sim | Não | Usa instância de Estoque da mesma aplicação; saldo e histórico ainda não são ACID |
| Gestão de Documentos | Sim | Não | CategoriaId opcional e texto legado preservado; arquivo compactado ainda fica no payload |
| Gestão de Usuários | Sim | Não | Perfil associado a e-mail normalizado; não valida identidade Google nem autoriza requisições |

## Vínculos e integridade

1. **Financeiro → Plano de Contas:** o serviço verifica referências antes da exclusão; o adaptador SQL possui FK com restrição. A operação completa ainda precisa ser validada em banco isolado sob concorrência.
2. **Acerto → Estoque:** o acerto usa a instância de Estoque construída na mesma aplicação. Atualização de saldo e gravação do histórico ainda são operações separadas em memória; PostgreSQL deve implementá-las em uma transação única, com bloqueio de linha e idempotência.
3. **Documento → Categoria:** `categoriaId` opcional; o nome da categoria é copiado para o campo textual legado `pasta`. A exclusão de categoria referenciada é bloqueada pelo serviço.
4. **Acerto → Motivo:** `motivoId` opcional; o nome do motivo é copiado para o texto legado `motivo`. A exclusão de motivo referenciado é bloqueada.
5. **Contas Bancárias → Financeiro:** não há vínculo de conciliação confirmado. Não apresentar saldo manual como saldo conciliado.
6. **Fornecedores/Moradores → Financeiro:** associação ainda não confirmada com as regras do sistema original; não criar relação por suposição.

## Riscos e gates pendentes

### Antes de qualquer dado real
- Completar adaptadores PostgreSQL e migrations para os módulos ainda em memória.
- Garantir atomicidade e concorrência em operações multi-entidade.
- Validar token Google no servidor, usar identidade verificada e implementar autorização por rota/ação. O campo `perfil` sozinho não protege endpoint.
- Definir CORS por allowlist exata.
- Definir proteção e auditoria de CPF, telefone, endereço, empregados, documentos e anexos.
- Configurar credenciais server-side com privilégio mínimo; nunca colocar segredos no frontend.

### Antes da homologação funcional
- Comparar schemas, campos, validações e regras com o HTML original em base sanitizada.
- Validar importação de moradores, anexos, formatos de arquivo e limites de payload.
- Definir paginação, filtros, trilha de auditoria, logs sem dados pessoais e tratamento de conflitos.
- Executar testes de integração e concorrência com PostgreSQL local isolado.
- Conectar e homologar as telas do frontend com a API, incluindo estados de erro e conflito.

### Antes da promoção ao sistema original
- Testes automatizados aprovados em CI para o commit exato.
- Comparação funcional com o original e evidências de equivalência.
- Backup/restauração e rollback ensaiados.
- Aprovação explícita antes de qualquer mudança na branch original ou banco de produção.

## Conclusão

O isolamento de serviços por instância está agora aplicado aos 15 routers. Isso corrige o acoplamento anterior dos routers com singletons globais, mas não significa que os 15 módulos estejam persistidos ou prontos para produção. Somente Formas Monetárias, Plano de Contas e Financeiro possuem adaptadores PostgreSQL neste estágio; os demais permanecem em memória. A próxima prioridade técnica é completar e testar persistência transacional para Estoque/Acertos e os cadastros restantes, sem tocar no original.

## Integridade do original

Esta revisão não altera o `index.html` original nem configura conexão com o banco de produção.
