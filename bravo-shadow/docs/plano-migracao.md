# Plano de migração gradual

## Etapa 0 — Proteção e inventário
- Manter o original isolado na branch `upgrade/project-hardening`.
- Desenvolver exclusivamente na branch `bravo-shadow`.
- Documentar módulos, fluxos, contratos de dados e integrações.
- Preparar ambiente de homologação isolado, sem escrita em produção.

## Etapa 1 — Fundação
- API FastAPI versionada.
- Configuração por ambiente e gestão segura de segredos.
- Logs estruturados, tratamento uniforme de erros e health checks.
- Testes automatizados e documentação OpenAPI.
- Definir autenticação Google/e-mail e autorização após auditoria do provedor atual.

## Etapa 2 — Contratos e dados
- Mapear o payload legado completo e suas regras.
- Definir schemas Pydantic de entrada e saída.
- Criar camada repository/service para isolar persistência e regras.
- Planejar ambiente de dados sombra com cópia sanitizada.
- Não alterar schema de produção nesta etapa.
- Não habilitar PostgreSQL até que a composição da aplicação seja isolada por instância, o schema local tenha sido aplicado e os testes reais de integração estejam aprovados.

## Etapa 3 — Piloto
- Capacidade inicial escolhida: Formas Monetárias, por ter CRUD simples e poucas dependências.
- API e interface sombra conectadas para listar, cadastrar, editar e excluir registros.
- Persistência ainda temporária em memória; não usar dados reais nem considerar este piloto homologado.
- Comparação estática com o HTML original concluída: campos `nome` e `multaPct`, multa padrão 2%, nome obrigatório e campo numérico com passo 0,01. O original não define limites mínimo/máximo nem tamanho máximo do nome; a sombra preserva esse comportamento, sem impor regras novas.
- Pipeline CI atualizado: build Docker e smoke test da interface/API aprovados; backend validado com PostgreSQL 16 descartável. Na execução `45894322542` (commit `adae893`), `360 passed, 1 warning`. A suíte inclui testes reais de concorrência, idempotência e rollback no PostgreSQL efêmero; isso não equivale a aplicar migrations ou conectar o banco original.
- Ainda pendente: validar o fluxo visual/funcional em navegador e medir latência/erros antes de avançar para outro domínio.
- Novo gate técnico antes da persistência real: eliminar o uso de serviços globais mutáveis no `create_app()` e injetar serviços/repositórios por instância FastAPI. O teste deve provar que duas aplicações com configurações de armazenamento diferentes não compartilham estado nem alteram a configuração uma da outra.
- Medir latência, erros e consistência antes de avançar para outro domínio.

## Etapa 4 — Migração por domínio
- Migrar uma capacidade por vez.
- Manter frontend e backend compatíveis durante a transição.
- Evitar escrita dupla em produção.
- Registrar versão do contrato e plano de rollback para cada etapa.

## Etapa 5 — Homologação final
- Cobrir fluxos críticos ponta a ponta.
- Validar permissões, RLS, auditoria, backup e restauração.
- Conferir integridade e reconciliação dos dados.
- Executar testes de carga proporcionais ao uso esperado.

## Etapa 6 — Promoção
- Exigir aprovação explícita.
- Fazer backup verificável.
- Implantar em janela controlada.
- Monitorar e manter caminho de reversão.

## Critérios de aceite
- Nenhuma funcionalidade crítica perdida.
- Resultados de negócio equivalentes ou aprovados.
- Nenhuma exposição indevida de dados.
- Sem erros críticos nos testes.
- Desempenho e experiência iguais ou melhores.
- Rollback testado e documentado.
