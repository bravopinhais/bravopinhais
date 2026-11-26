# Revisão de integração e arquitetura — Bravo Shadow

## Estado da revisão — 26/11/2026

Revisão estática da branch `bravo-shadow`. Os 15 routers foram inspecionados e todos resolvem seus serviços por `request.app.state.services`; nenhum dos routers inspecionados importa diretamente um singleton de serviço. A composição de serviços está concentrada em `build_storage_services()`, chamada por `create_app()`.

Esta verificação é de código-fonte. O CI do commit `79d97af` concluiu com sucesso para a política de imutabilidade de acertos persistidos. As alterações de precisão monetária para Contas Bancárias passaram no CI do commit `cfd3211` (run `45843573270`). Isso não representa teste de browser, teste de banco PostgreSQL real ou homologação funcional.

## Arquitetura atual

- Uma aplicação FastAPI integrada, com 15 módulos/recursos e API versionada em `/api/v1`.
- Serviços e repositórios construídos por instância de aplicação e expostos em `app.state.services`.
- Repositório em memória como padrão seguro; adequado a desenvolvimento/testes, não a produção, multi-worker ou persistência após reinício.
- Adaptadores PostgreSQL estão conectados no `build_storage_services()` para os 14 módulos com repositório próprio. O saldo bancário usa `Decimal` no contrato Python e `numeric(14,2)` no SQL, mantendo o JSON numérico legado: Plano de Contas, Financeiro, Formas Monetárias, Contas Bancárias, Moradores, Fornecedores, Empregados, Estoque, Acertos de Estoque, Categorias, Motivos de Acerto, Documentos, Condomínio, Conselho e Usuários. O Dashboard não tem repositório próprio; seus indicadores ainda são demonstrativos.
- O frontend sombra pode ser servido pelo processo FastAPI, mas a integração completa de todas as telas com as APIs ainda não foi homologada.
- CORS permanece fechado até definição de allowlist.
- Nenhuma conexão com banco de produção foi configurada ou executada.

## Matriz dos 15 módulos

| Módulo | Serviço por aplicação | Persistência PostgreSQL | Observações |
|---|---|---|---|
| Dashboard | Não possui serviço próprio | Não | Indicadores atuais são demonstrativos; falta endpoint agregado |
| Condomínio | Sim | Sim, adaptador existente | Cadastro institucional único; atualização parcial preserva campos não enviados |
| Conselho | Sim | Sim, adaptador existente | CRUD de conselheiros |
| Plano de Contas | Sim | Sim, adaptador existente | Verifica referências financeiras; restrição final deve ser garantida no banco |
| Contas a Pagar/Receber | Sim | Sim, adaptador existente | Usa `planoContaId`; vínculo opcional no contrato atual |
| Formas Monetárias | Sim | Sim, adaptador existente | Piloto de persistência |
| Contas Bancárias/Caixa | Sim | Sim, adaptador existente | Saldo informado/manual com precisão Decimal/numeric(14,2); não equivale a conciliação bancária |
| Moradores/Unidades | Sim | Sim, adaptador existente | Dados pessoais; filtros/importação em lote ainda precisam de validação funcional |
| Fornecedores | Sim | Sim, adaptador existente | Vínculo financeiro não confirmado |
| Empregados | Sim | Sim, adaptador existente | Dados pessoais exigem controles de privacidade |
| Pastas/Categorias | Sim | Sim, adaptador existente | Documentos podem apontar para categoria por ID; exclusão referenciada é bloqueada |
| Estoque/Inventário | Sim | Sim, adaptador existente | CRUD de produtos; edição ainda precisa de política concorrente |
| Acerto de Estoque | Sim | Sim, adaptador existente | Criação atômica com `FOR UPDATE`; exclusão persistida bloqueada até existir estorno compensatório |
| Gestão de Documentos | Sim | Sim, adaptador existente | CategoriaId opcional e texto legado preservado; arquivo compactado ainda fica no payload |
| Gestão de Usuários | Sim | Sim, adaptador existente | Perfil associado a e-mail normalizado; não valida identidade Google nem autoriza requisições |

## Vínculos e integridade

1. **Financeiro → Plano de Contas:** o serviço verifica referências antes da exclusão; o adaptador SQL possui FK com restrição. A operação completa ainda precisa ser validada em banco isolado sob concorrência.
2. **Acerto → Estoque:** no modo PostgreSQL, criação de movimento bloqueia a linha do produto com `FOR UPDATE`, atualiza saldo e insere histórico na mesma transação. Exclusão de movimentos persistidos retorna HTTP 409 até existir fluxo de estorno compensatório. Edição destrutiva também não deve ser introduzida.
3. **Documento → Categoria:** `categoriaId` opcional; o nome da categoria é copiado para o campo textual legado `pasta`. A exclusão de categoria referenciada é bloqueada pelo serviço.
4. **Acerto → Motivo:** `motivoId` opcional; o nome do motivo é copiado para o texto legado `motivo`. A exclusão de motivo referenciado é bloqueada.
5. **Contas Bancárias → Financeiro:** não há vínculo de conciliação confirmado. Não apresentar saldo manual como saldo conciliado.
6. **Fornecedores/Moradores → Financeiro:** associação ainda não confirmada com as regras do sistema original; não criar relação por suposição.

## Riscos e gates pendentes

### Antes de qualquer dado real
- Criar e validar migration formal pela Supabase CLI; o SQL atual continua sendo rascunho cumulativo, não executado.
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

O isolamento de serviços por instância está agora aplicado aos 15 routers. Isso corrige o acoplamento anterior dos routers com singletons globais, mas não significa que os 15 módulos estejam persistidos ou prontos para produção. Os 14 módulos com repositório próprio têm adaptadores PostgreSQL ligados à composição de serviços da branch sombra; o Dashboard ainda não possui endpoint agregado. Isso comprova a existência e o wiring dos adaptadores, não sua validação contra um PostgreSQL real. A migration formal ainda não foi criada ou aplicada. A próxima prioridade é validar o SQL/mapeamentos e rodar os testes de integração em PostgreSQL local isolado, sem tocar no original.

## Integridade do original

Esta revisão não altera o `index.html` original nem configura conexão com o banco de produção.


## Gate de autorização PostgreSQL identificado na revisão

O SQL atual habilita RLS nas 15 tabelas, não cria policies e revoga grants de `public`, `anon`, `authenticated` e `service_role`. Isso mantém as tabelas fora do acesso padrão da Data API, mas também bloqueia uma role de API comum mesmo que receba privilégios SQL de tabela: RLS sem policy aplicável nega as linhas. Antes de habilitar `BRAVO_STORAGE_BACKEND=postgres`, definir e testar uma role customizada e policies explícitas para ela. Não usar `BYPASSRLS` nem superusuário como atalho de produção.

O modo PostgreSQL atual instancia adaptadores para todos os 14 módulos com repositório próprio. Portanto, um usuário de API não pode receber GRANTs apenas nas três tabelas financeiras. A matriz de privilégios deve cobrir as 15 tabelas, com exceção deliberada de UPDATE/DELETE em `acertos_estoque`, cujo histórico deve permanecer imutável.

## Proteção de saldo de estoque

No adaptador PostgreSQL, a edição geral do produto agora bloqueia a linha com `FOR UPDATE` e verifica a existência de movimentos. Se houver histórico, a quantidade não pode ser alterada pelo CRUD cadastral; mudanças de saldo devem ocorrer pelo fluxo transacional de acerto. Isso impede que uma edição de cadastro reescreva o saldo sem registrar movimento.
