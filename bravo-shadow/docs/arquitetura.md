# Arquitetura-alvo — Bravo Shadow

## Visão geral

Aplicação única e integrada, com frontend web e backend modular organizado por domínio. Os módulos não serão aplicações independentes.

```text
Frontend web unificado (HTML/CSS/JS)
              |
       API REST versionada
              |
       Python / FastAPI
       |      |       |
    módulos serviços repositórios
              |
       camada de persistência
              |
       Supabase / PostgreSQL
```

## Responsabilidades

### Frontend
- Renderização, navegação, acessibilidade e experiência visual.
- Estado transitório da interface.
- Chamadas à API por contratos documentados.
- Não conter regras críticas de autorização ou segredos.

### Backend
- Regras de negócio, validações e cálculos.
- Serviços de domínio e orquestração.
- Autorização de operações e validação de identidade.
- Logs, auditoria e tratamento uniforme de erros.

### Dados
- Supabase/PostgreSQL permanece como referência até a auditoria do modelo atual.
- A tabela legada `condominio_dados` e seu campo `payload` serão tratados como contrato legado a investigar, não como autorização para alterações.
- Nenhuma migração destrutiva ou alteração de schema nesta fase.
- Ambiente sombra deverá usar projeto/banco separado ou cópia sanitizada.

## Segurança
- Segredos somente em variáveis de ambiente/secret manager.
- Nunca expor service-role keys no navegador.
- Validar identidade e permissões no servidor.
- Preservar o fluxo Google/e-mail; detalhes do provedor e dos claims serão confirmados antes da implementação.
- CORS por allowlist explícita.
- Dados pessoais de produção não devem ser copiados sem minimização e proteção.

## Estratégia de transição
- Strangler gradual: cada capacidade nova passa a ser atendida pela API sombra após homologação.
- O frontend original permanece operacional durante o desenvolvimento.
- Sem escrita dupla em produção.
- Comparação de resultados e trilha de auditoria antes de cada promoção.
- Rollback documentado por etapa.


## Gate de integração

A composição modular da API não significa que os módulos estejam prontos para operação: persistência, transações, autorização server-side, CORS por allowlist, observabilidade e testes de integração são pré-requisitos. Ver `revisao-integracao-arquitetura.md`.
