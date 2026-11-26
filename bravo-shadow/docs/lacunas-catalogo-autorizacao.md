# Lacunas do catálogo de autorização — Bravo Shadow

## Status

Auditoria estática e proposta de correção. Nenhum código, rota, permissão, banco ou interface foi alterado.

## Achados

### 1. Gestão de usuários usa capacidades amplas demais

O catálogo atual define `usuarios:create`, `usuarios:update` e `usuarios:delete`. O contrato de gestão de usuários exige separar operações cadastrais das administrativas. Com a capacidade `usuarios:update` única, uma rota PUT integral pode misturar alteração de nome/cargo com perfil/status. A capacidade `usuarios:create` também não distingue cadastro comum de provisionamento/promoção administrativa.

**Recomendação:** não reutilizar essas três capacidades para uma futura API de usuários. Criar capacidades distintas, por exemplo `usuarios:read`, `usuarios:create`, `usuarios:update_profile`, `usuarios:update_status` e `usuarios:deactivate`, e manter o cadastro inicial fora de endpoint público. Se houver edição cadastral comum, separar também `usuarios:update_data`. A nomenclatura final deve acompanhar os endpoints efetivamente desenhados.

### 2. Operações de estoque precisam expressar a regra de domínio

O catálogo tem `estoque:create` e `estoque:update`, enquanto o domínio distingue cadastro de produto de movimentação de saldo. A movimentação está separada em `acertos_estoque:create`, o que é positivo, mas `estoque:update` pode parecer autorização para alterar quantidade diretamente.

**Recomendação:** documentar explicitamente que `estoque:update` permite apenas metadados e nunca saldo. Considerar nome mais específico como `estoque:update_metadata` quando os contratos de rota forem estabilizados. Manter movimentos sem UPDATE/DELETE.

### 3. Dashboard e relatórios são capacidades sem endpoint HTTP confirmado

`dashboard:read` e `relatorios:read` aparecem no catálogo, mas a auditoria não encontrou endpoints HTTP de agregação.

**Recomendação:** manter essas capacidades sem efeito até existirem endpoints protegidos e testes próprios. Não conceder acesso indireto aos módulos de origem por meio delas.

### 4. Perfis são uma camada de agrupamento, não a autorização em si

A política atual concede todas as capacidades enumeradas ao Admin e nenhuma ao Operador. Isso é uma postura técnica fail-closed, mas não representa uma matriz funcional aprovada. O perfil Admin não deve ser tratado como autorização universal para ações futuras que ainda não estejam no catálogo.

**Recomendação:** manter o catálogo fechado e versionado; aprovar as capacidades do Operador por ação antes de concedê-las. Para operações críticas, exigir também regras contextuais (por exemplo, impedir autoalteração e proteger o último Admin), não apenas a capacidade estática.

### 5. Auditoria é requisito transversal ainda não representado no catálogo

Alterações de perfil/status, operações financeiras sensíveis, importação de moradores e movimentos de estoque exigem trilha de auditoria. Não há capacidade específica para consultar ou administrar logs.

**Recomendação:** definir um serviço de auditoria append-only e política de acesso própria. A capacidade de consultar logs não deve ser inferida de `usuarios:read` nem de `dashboard:read`.

## Checklist antes de integrar dependências nas rotas

- [ ] Confirmar nomes canônicos e granularidade das capacidades.
- [ ] Separar gestão cadastral de gestão de perfil/status.
- [ ] Confirmar que atualização de produto não altera saldo.
- [ ] Definir endpoints reais de Dashboard/Relatórios antes de conceder acesso.
- [ ] Definir política de auditoria, consulta e retenção.
- [ ] Aprovar explicitamente a matriz de Admin e Operador.
- [ ] Cobrir cada rota com teste de identidade ausente (401), capacidade ausente (403), sucesso autorizado e conta inativa.
- [ ] Cobrir regras contextuais: autoelevação, último Admin e imutabilidade de movimentos.

## Conclusão

O catálogo atual é uma fundação técnica útil, mas ainda não deve ser ligado aos routers. A prioridade é refinar a granularidade de gestão de usuários e estoque, definir auditoria e obter aprovação funcional. Até lá, manter a API sombra privada e sem dados reais.