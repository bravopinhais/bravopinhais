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

## Etapa 3 — Piloto
- Capacidade inicial escolhida: Formas Monetárias, por ter CRUD simples e poucas dependências.
- API e interface sombra conectadas para listar, cadastrar, editar e excluir registros.
- Persistência ainda temporária em memória; não usar dados reais nem considerar este piloto homologado.
- Próximos critérios: executar testes automatizados, validar o fluxo no navegador e comparar regras/campos com o original.
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
