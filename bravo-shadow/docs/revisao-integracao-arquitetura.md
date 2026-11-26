# Revisão de integração e arquitetura — Bravo Shadow

## Escopo e método
Revisão estática dos serviços, composição FastAPI, dependências e documentação na branch `bravo-shadow`. Não foi executada a aplicação, não foram rodados testes e não houve conexão com Supabase. A branch original `upgrade/project-hardening` foi consultada apenas para preservar o contrato já inventariado.

## Diagnóstico executivo
A sombra possui 15 módulos/recursos com rotas registradas em uma aplicação FastAPI única, mas ainda é um protótipo de contratos: os serviços usam dicionários em memória, sem repositórios persistentes, transações, isolamento entre processos ou recuperação após reinício. O frontend também não consome essas APIs.

**Conclusão:** não liberar para dados reais nem promover para o sistema original nesta fase.

## Composição da aplicação
- Um único objeto FastAPI em `backend/app/main.py`.
- Os 15 routers são registrados no mesmo processo.
- Cada serviço instancia seu próprio armazenamento em memória.
- A ligação Plano de Contas → Financeiro é feita manualmente no `main.py`, atribuindo um callback a um atributo privado do serviço.
- **Novo achado de isolamento:** `create_app()` chama `configure_storage()`, que substitui repositórios em objetos de serviço globais (`plano_contas_service`, `financeiro_service`, `formas_monetarias_service`). Os routers importam esses singletons diretamente. Assim, criar duas instâncias FastAPI com configurações diferentes no mesmo processo pode fazer uma aplicação usar o armazenamento configurado pela outra. O teste atual restaura manualmente o modo `memory`, o que evita parte da interferência no teste, mas não resolve o acoplamento estrutural.
- `CORSMiddleware` está importado, mas não está configurado nem adicionado à aplicação. A API não possui política CORS efetiva.
- A dependência `email-validator` foi adicionada para suportar o tipo `EmailStr` no perfil de usuário.

## Matriz de dependências e integridade

| Origem | Destino | Vínculo atual | Risco / trabalho necessário |
|---|---|---|---|
| Financeiro | Plano de Contas | `planoContaId` opcional; checker impede exclusão de conta referenciada | Sem FK no banco; serviço de vínculo consulta apenas memória local; concorrência entre gravação financeira e exclusão não é transacional |
| Acertos de Estoque | Estoque | `produtoId`; entrada/saída altera quantidade | Alteração do saldo e gravação do histórico são operações separadas; precisam de uma transação atômica e controle de concorrência |
| Documentos | Pastas/Categorias | `pasta` é texto, não ID | Renomear/excluir pasta pode deixar documentos com nome antigo; decidir migração para ID mantendo compatibilidade |
| Acertos de Estoque | Motivos de Acerto | Motivo gravado como texto | Sem integridade referencial; exclusão/renomeação não atualiza históricos |
| Dashboard / DRE | Financeiro e Plano de Contas | Leituras agregadas planejadas | Não há endpoint agregado nem fonte persistente; regras atuais do original incluem limitações de data/status |
| Usuários | Identidade Google/e-mail | Perfil contém e-mail normalizado | Sem validação de token, identidade verificada, sessão ou autorização no backend |
| Contas Bancárias | Financeiro | Nenhum vínculo confirmado | Saldo bancário manual não pode ser tratado como saldo conciliado |
| Fornecedores / Moradores | Financeiro | Nenhum vínculo no contrato atual | Não inventar associação até confirmar regra de negócio original |

## Riscos técnicos prioritários

### P0 — antes de qualquer dado real
1. **Persistência:** substituir os dicionários em memória por repositórios PostgreSQL/Supabase de homologação, com migrações versionadas, chaves e constraints. Manter o banco de produção fora do escopo.
2. **Transações:** garantir atomicidade em Acerto de Estoque (saldo + histórico) e nas verificações/exclusões de Plano de Contas. Implementar bloqueio/controle otimista para atualizações concorrentes.
3. **Autorização:** validar token Google no servidor, obter e-mail verificado do token validado e aplicar permissões por rota/ação. O campo `perfil` sozinho não protege endpoint algum.
4. **CORS:** configurar middleware com allowlist exata para os domínios de desenvolvimento/homologação; não usar curinga com credenciais.
5. **Privacidade:** definir controle de acesso e auditoria para CPF, telefone, endereço, dados de empregados, documentos e anexos.

### P1 — antes da homologação funcional
6. **Isolamento por aplicação:** remover a mutação de serviços globais no `configure_storage`; construir repositórios/serviços por instância e injetá-los nos routers via dependências FastAPI ou `app.state`. Adicionar teste que cria duas aplicações com storages distintos e comprova que uma não altera a outra. Fazer isso antes de executar testes de integração com múltiplas configurações.
7. **Contratos e relações:** documentar IDs, campos opcionais, regras de exclusão, estados e erros HTTP; introduzir FKs ou relações explícitas quando a regra for confirmada.
8. **Arquivos:** validar tamanho, MIME, extensão, limites de memória, integridade e compatibilidade do formato deflate/Base64 legado. Considerar armazenamento de objetos separado do payload JSON.
9. **Concorrência e idempotência:** definir versão/ETag ou `updated_at` + versão, idempotency key para operações de movimento e tratamento de conflito.
10. **Paginação e filtros:** evitar listagens ilimitadas à medida que os cadastros crescerem.
11. **Observabilidade:** logs estruturados com request ID, métricas, trilha de auditoria e mensagens de erro sem dados pessoais.

### P2 — antes da promoção
11. Testes automatizados executados em CI, testes de integração com banco isolado, testes de concorrência e restauração de backup.
12. Frontend sombra conectado à API, com estados de carregamento/erro, tratamento de 401/403/409 e sem acesso direto ao banco.
13. Comparação de resultados com o original em base sanitizada e plano de rollback testado.

## Decisões recomendadas para a próxima etapa
- Manter FastAPI como backend único e modular; não dividir os módulos em aplicações independentes.
- Criar camada de repositórios e migrações para PostgreSQL no ambiente sombra isolado.
- Preservar os contratos públicos atuais inicialmente, mas não congelar schemas antes de uma revisão de paridade.
- Priorizar primeiro a persistência e testes de integração de Plano de Contas/Financeiro e Estoque/Acertos, pois são os vínculos operacionais mais sensíveis.
- Não ativar ainda autenticação/permissões, arquivos ou escrita real até concluir seus gates de segurança.

## Critérios para considerar a integração pronta
- Dados sobrevivem a reinício e estão isolados por ambiente.
- Operações multi-entidade são atômicas.
- Restrições de referência são garantidas no banco e na camada de serviço.
- Cada endpoint protegido exige identidade validada e permissão explícita.
- CORS usa allowlist e não há segredos no frontend.
- Testes de unidade, integração, concorrência e backup/restauração passam em CI.
- Frontend chama exclusivamente a API e erros são apresentados de forma previsível.

## Integridade do original
Esta revisão não altera o `index.html` original e não configura conexão com o banco de produção.
