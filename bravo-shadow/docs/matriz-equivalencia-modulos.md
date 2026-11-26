# Matriz de equivalência funcional — Bravo original x Bravo Shadow

## Objetivo e escopo

Esta matriz inicia a Fase 0 da migração híbrida e gradual. Compara o legado na branch `upgrade/project-hardening` com a versão sombra na branch `bravo-shadow`. É um inventário técnico inicial, não um aceite funcional nem autorização de corte.

**Regras de segurança:** o original é somente leitura; nenhuma escrita foi feita nele. Nenhuma base de produção foi consultada, conectada ou alterada. Não houve migração de dados, troca de tráfego ou alteração de autenticação/login.

## Baselines verificadas nesta inspeção

| Artefato | Branch | Blob SHA |
|---|---|---|
| `index.html` original | `upgrade/project-hardening` | `873dbf37bbcf2082faa0444ac28cb9ca9f8ff21c` |
| `bravo-shadow/frontend/index.html` | `bravo-shadow` | `2dfc65b42c52eae90b14bfd272c0d99458a8749f` |
| `bravo-shadow/backend/app/main.py` | `bravo-shadow` | `421490608922cd01e84c7d544199723d994d831b1` |

O legado tem 2.838 linhas nesta baseline. O roteador de conteúdo do original contém renderizadores dedicados para os 15 domínios, incluindo `renderDashboardView`, `renderCondominioView`, `renderPlanoContasView`, `renderFinanceiroView`, `renderFormasMonetariasView`, `renderContasBancariasView`, `renderMoradoresView`, `renderFornecedoresView`, `renderEmpregadosView`, `renderCategoriasView`, `renderEstoqueView`, `renderAcertoEstoqueView`, `renderDocumentosView`, `renderUsuariosView` e `renderRelatoriosCentralView`.

No Shadow, os 15 domínios aparecem na navegação, mas a própria interface informa que os módulos ainda não executam operações de negócio, com exceção do fluxo de Formas Monetárias. A API registra routers para os domínios operacionais; Dashboard tem serviço agregado, mas não router/endpoints próprios.

## Legenda de situação

- **UI:** interface navegável / fluxo de tela.
- **API:** router e endpoints no backend.
- **Persistência:** adaptador PostgreSQL existente não equivale a migration aplicada nem a teste real de banco.
- **Paridade:** não declarar concluída até comparar campos, regras, permissões, dados e resultados do legado.

## Matriz inicial por módulo

| Módulo | Evidência no legado | Situação Shadow observada | Lacuna principal / dependência |
|---|---|---|---|
| Dashboard | `renderDashboardView`; gráficos de receitas/despesas, ocupação e estoque; funções de inicialização de gráficos | Tela inicial com indicadores explicitamente ilustrativos; existe `DashboardService`, sem router de dashboard | Definir métricas e filtros equivalentes; endpoints agregados; só usar dados reais de módulos aceitos; não exibir zeros fictícios |
| Condomínio & Conselho | `renderCondominioView`, `salvarDadosCondominio`; renderização institucional e dados do conselho | Navegação/placeholder; backend possui routers separados para condomínio e conselheiros | Conferir todos os campos, concessionárias, composição do conselho, cardinalidade e regras de atualização |
| Plano de Contas | `renderPlanoContasView`; cadastro/edição e classificação | Navegação/placeholder; router e persistência no backend | Comparar hierarquia, códigos, natureza, obrigatoriedade e referências financeiras; manter integridade referencial |
| Contas a Pagar / Receber | `renderFinanceiroView`; títulos e classificações | Navegação/placeholder; router e persistência no backend | Faltam no contrato Shadow datas/status/baixa e vínculo bancário necessários a vários relatórios; mapear regras reais antes de ampliar |
| Formas Monetárias | `renderFormasMonetariasView` | Primeiro fluxo Shadow conectado: listar, criar, editar e excluir via API | Validar equivalência de campos, duplicidade, impacto em registros existentes e comportamento de exclusão; único candidato a piloto de UI, ainda sem aceite |
| Contas Bancárias / Caixa | `renderContasBancariasView` | Navegação/placeholder; router e persistência no backend | Saldo atual é manual; esclarecer origem do saldo, conciliação, movimentações e vínculo com Financeiro |
| Moradores & Unidades | `renderMoradoresView`, `filtrarMoradoresBloco`; também existe importação de planilha de moradores | Navegação/placeholder; router e persistência no backend | Inventariar campos pessoais, unidades/blocos, filtros, importação, duplicidades e privacidade; dados exigem controles de acesso |
| Fornecedores | `renderFornecedoresView` | Navegação/placeholder; router e persistência no backend | Comparar campos fiscais/contato, validações, duplicidade e relações com lançamentos |
| Empregados | `renderEmpregadosView`; inclui contato de emergência | Navegação/placeholder; router e persistência no backend | Conferir dados funcionais e contato de emergência, acesso restrito e regras de atualização |
| Pastas & Categorias | `renderCategoriasView`; há também exclusão de motivo de acerto | Navegação/placeholder; routers separados para categorias e motivos de acerto | Confirmar se “pastas”, categorias e motivos são entidades distintas; mapear referências e bloqueios de exclusão |
| Estoque & Inventário | `renderEstoqueView`, visualização de foto, gráfico de status e processamento de foto compactada | Navegação/placeholder; router e persistência no backend | Comparar campos de produto, marca/linha/fabricante, fotos, códigos, quantidade, níveis, filtros e scanner; distinguir edição de metadados de movimentação |
| Acerto de Estoque | `renderAcertoEstoqueView`, busca/filtro de produtos e exclusão de acerto | Navegação/placeholder; router e persistência no backend | Preservar histórico imutável, motivos, cálculo de saldo e atomicidade entre movimento e estoque; auditoria é pré-requisito |
| Gestão de Documentos | `renderDocumentosView`, visualizar/baixar documento e processamento gzip | Navegação/placeholder; router e persistência no backend | Mapear formato gzip/base64, nome original, MIME, limites, visualização/download, categorias e estratégia de arquivos |
| Relatórios & DRE | `renderRelatoriosCentralView`; funções de relatório e integração de gráficos | Navegação/placeholder; não há API própria de relatórios/DRE | Definir fórmulas, períodos, competência/caixa, filtros, agrupamentos e reconciliação com Financeiro/Plano de Contas |
| Gestão de Usuários | `renderUsuariosView`; cadastro e administração legados | Navegação/placeholder; router existe, mas rotas de negócio seguem sem proteção | Separar cadastro, perfil e status; Google ID token; matriz de capacidades aprovada; provisionamento seguro do primeiro Admin |

## Componentes transversais identificados

1. **Persistência do legado:** o original inicializa cliente Supabase diretamente no frontend e contém funções de salvamento/carregamento. Antes de importar qualquer dado, identificar tabelas, chaves, políticas, relacionamentos, formatos e origem de cada coleção. Não reutilizar credenciais nem conectar Shadow ao projeto de produção.
2. **Arquivos:** o legado comprime arquivos/fotos em gzip e base64 no navegador e possui fluxos de visualizar/baixar. O Shadow preserva conteúdo comprimido em contratos existentes, mas não tem estratégia de armazenamento externo migrada.
3. **Importação/exportação:** há funções de exportação para CSV e importação de planilha de moradores. Esses fluxos precisam de especificação própria, incluindo erros por linha, duplicidade e reprocessamento.
4. **Navegação e estado:** o legado tem renderização de módulos, abas, modais e estado de filtros. O Shadow ainda possui navegação simples e um fluxo de Formas Monetárias.
5. **Autenticação e autorização:** o original tem telas/fluxos de login e primeiro acesso. O Shadow tem fundação de validação Google no backend, mas o Client ID não está configurado e as rotas de negócio não estão protegidas. Não ativar exposição pública nem introduzir senha local.
6. **Dashboard/DRE:** os resultados históricos não podem ser reproduzidos com segurança apenas com os campos financeiros atuais; faltam datas/status de liquidação e associação bancária. Regras e limitações estão detalhadas em `auditoria-dashboard-relatorios-dre.md`.

## Status geral desta fase

- [x] Baseline do original identificada e SHA registrado.
- [x] Lista dos 15 módulos confirmada no roteador do legado e na navegação Shadow.
- [x] Renderizadores e funções transversais mais relevantes identificados.
- [x] Diferença entre presença visual, API e persistência explicitada.
- [x] Fichas estáticas de coleções dos lotes 01 a 06 elaboradas: Condomínio/Conselho/Plano de Contas; Financeiro/Formas Monetárias/Contas Bancárias; Moradores/Fornecedores/Empregados; Categorias/Motivos; Estoque/Acertos; Documentos.
- [x] Principais incompatibilidades já identificadas nos seis lotes, incluindo preservação de IDs, datas históricas, movimentos de estoque, referências textuais e arquivos Gzip.
- [ ] Inventário completo de campos por tela e formulário para todos os módulos.
- [ ] Inventário de regras de negócio e validações por operação.
- [x] Mapa estrutural inicial de coleções, IDs e relacionamentos consolidado em `revisao-consolidada-dependencias-fase0.md`, com vínculos confirmados separados de hipóteses e pendências.\n- [ ] Conferência do mapa contra payload autorizado, cardinalidades e política aprovada para cada classe de órfão.
- [ ] Inventário de relatórios, importações/exportações e formatos de arquivos.
- [ ] Matriz de permissões por operação aprovada.
- [ ] Critérios de aceite e reconciliação definidos por módulo.
- [ ] Testes executados e evidências registradas.

## Próxima sequência recomendada

1. Completar as fichas da Fase 0 para Dashboard/Relatórios/DRE e Gestão de Usuários, incluindo métricas, fórmulas, filtros, operações, permissões e dependências.
2. Validar a matriz estrutural de relacionamentos contra payload autorizado e formalizar cardinalidades e política de órfãos, sem usar dados reais nesta etapa.
3. Fazer especificação detalhada de um módulo cadastral de baixo risco, comparando cada formulário e ação com o contrato Shadow.
4. Validar localmente o backend e os adaptadores com banco descartável, depois de migrations e políticas revisadas.
5. Só então propor o piloto de importação com dados sintéticos/anonimizados, relatório de divergências e rollback ensaiado.

A CI da branch bravo-shadow executou build/smoke test Docker e 360 testes backend aprovados contra PostgreSQL descartável no run 45894322542. Essa evidência valida a suíte automatizada, mas não substitui a conclusão das fichas restantes, validação visual em navegador, revisão de segurança ou aceite funcional.

**Não é aceite de migração:** nenhuma linha desta matriz autoriza corte, escrita dupla, mudança de roteamento, migração de dados reais ou alteração do original. As descrições de campos e regras ainda precisam ser verificadas nos formulários e operações completos antes da implementação.
