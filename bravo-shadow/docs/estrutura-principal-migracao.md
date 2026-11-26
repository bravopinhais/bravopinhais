# Estrutura principal de migração — Bravo para Bravo Shadow

## Objetivo

Organizar a evolução do Bravo original para a arquitetura Bravo Shadow por etapas controladas, mantendo a operação existente preservada até que cada módulo substituto esteja validado. A estratégia aprovada é **híbrida e gradual**: desenvolver e validar no Shadow, migrar por domínio funcional e só então promover cada etapa.

Este documento é o roteiro de migração. Não autoriza alteração no sistema original, migração de dados reais, troca de domínio, publicação ou corte de tráfego.

## Princípios obrigatórios

1. **Shadow primeiro:** implementação, testes e validação acontecem em bravo-shadow/ na branch bravo-shadow.
2. **Original preservado:** não modificar, mover ou renomear o index.html original durante a preparação.
3. **Uma fonte de verdade por módulo:** durante a convivência, cada domínio tem um sistema responsável por gravar os dados. Não habilitar escrita dupla improvisada.
4. **Migração reversível:** cada etapa precisa de backup/restore validado, critério de aceite e plano de retorno antes do corte.
5. **Compatibilidade explícita:** contratos, IDs, formatos, datas, valores monetários, anexos e relacionamentos precisam ser mapeados antes da carga.
6. **Sem dados de produção no Shadow de desenvolvimento:** usar dados sintéticos ou cópias anonimizadas formalmente autorizadas. Não conectar o Shadow ao banco original.
7. **Segurança antes de exposição:** nenhuma API de negócio pode ser exposta enquanto suas rotas não exigirem autenticação Google validada e autorização por capacidade.
8. **Sem migração big-bang:** migrar domínio por domínio, mantendo os demais no sistema vigente.
9. **Observabilidade e auditoria:** registrar versão, etapa, contagens, divergências e resultado sem despejar dados pessoais ou segredos nos logs.
10. **Sem prometer conclusão:** build, testes, reconciliação e deploy só são considerados concluídos quando houver evidência executada.

## Visão de arquitetura durante a transição

- **Bravo original:** permanece operacional e é a referência dos módulos ainda não migrados.
- **Bravo Shadow:** recebe os módulos reimplementados, API, persistência e testes.
- **Camada de integração temporária:** contratos/adaptadores versionados para comunicação controlada entre os sistemas, se necessária. Não compartilhar diretamente estado interno nem banco.
- **Roteamento por módulo:** a interface pode encaminhar um módulo ao Shadow somente depois de seu aceite. Os demais continuam no original.
- **Dados:** cada módulo tem proprietário de escrita definido. A leitura cruzada deve ser explicitamente documentada e temporária.

## Inventário funcional e dependências

| Domínio | Dependências principais | Ordem sugerida |
|---|---|---:|
| Identidade, usuários e permissões | Google ID token, cadastro interno, matriz de capacidades, auditoria | Fundação transversal |
| Condomínio e Conselho | Identidade e governança | 1 |
| Categorias e Motivos de Acerto | Cadastros auxiliares | 2 |
| Fornecedores e Empregados | Identidade e cadastros | 3 |
| Moradores e Unidades | Identidade, privacidade e autorização reforçadas | 4 |
| Plano de Contas | Base de classificação financeira | 5 |
| Formas Monetárias | Cadastro financeiro auxiliar | 6 |
| Contas Bancárias e Caixa | Regras de saldo e reconciliação ainda a definir | 7 |
| Contas a Pagar/Receber | Plano de Contas; associação bancária e datas/status ainda incompletos | 8 |
| Estoque e Inventário | Categorias auxiliares e catálogo de produtos | 9 |
| Acerto de Estoque | Estoque, motivos e auditoria transacional | 10 |
| Pastas e Gestão de Documentos | Categorias, privacidade e estratégia de arquivos | 11 |
| Dashboard | APIs agregadas e dados reais dos módulos já migrados | 12 |
| Relatórios e DRE | Financeiro, Plano de Contas e regras contábeis aprovadas | 13 |

A numeração é uma sequência técnica inicial, não uma autorização para migrar nem uma definição final de prioridade operacional. Identidade, autorização e auditoria são pré-requisitos transversais, não um módulo que possa ser ignorado.

## Fases e portões de aceite

### Fase 0 — Congelamento e inventário do legado

- Identificar versão/commit de referência do original.
- Inventariar telas, ações, campos, regras, relatórios, integrações e formatos armazenados.
- Identificar IDs, referências, dados obrigatórios, campos opcionais e comportamentos implícitos.
- Registrar lacunas e regras desconhecidas sem inventar regras de negócio.

**Aceite:** inventário revisado; baseline do original preservada; nenhuma alteração funcional no legado.

### Fase 1 — Fundação técnica do Shadow

- Consolidar frontend integrado, API versionada e contratos por módulo.
- Fechar configuração por ambiente, health check, logs seguros e tratamento de erros.
- Definir PostgreSQL local de desenvolvimento e migrations versionadas.
- Validar isolamento de serviços por aplicação, repositórios e transações.
- Criar pipeline de testes e evidências reproduzíveis.

**Aceite:** ambiente local reproduzível; migrations locais revisadas; testes automatizados executados; nenhuma dependência de dados ou banco de produção.

### Fase 2 — Segurança transversal

- Configurar Google OAuth Client ID somente no ambiente seguro.
- Validar ID token no servidor e vínculo inequívoco com cadastro interno.
- Aprovar matriz de capacidades por operação e perfil.
- Separar cadastro, administração e desativação de usuários.
- Provisionar primeiro Admin fora da API pública, com procedimento revisado.
- Integrar auditoria transacional às operações sensíveis.
- Proteger cada rota e testar 401, 403 e acesso permitido.

**Aceite:** matriz aprovada; rotas protegidas individualmente; bootstrap controlado; testes de autorização e auditoria executados. Até aqui, não expor rotas de negócio publicamente.

### Fase 3 — Migração-piloto de baixo risco

- Selecionar um domínio cadastral com dependências limitadas.
- Mapear campos e regras legado → Shadow.
- Criar importador repetível, com modo de simulação, validação e relatório de divergências.
- Testar importação em base local descartável com dados sintéticos/anonimizados.
- Comparar contagens, IDs, campos, relacionamentos e comportamento da interface.
- Exercitar backup, restauração e retorno ao módulo original.

**Aceite:** reconciliação sem divergências não explicadas; operação funcional validada; rollback ensaiado. Só então avaliar corte controlado do piloto.

### Fase 4 — Migração dos domínios dependentes

Executar em lotes pequenos, respeitando a matriz de dependências. Para cada módulo repetir o ciclo:

1. Especificação funcional e mapeamento de dados.
2. Implementação Shadow e testes unitários/integração.
3. Importação de ensaio e reconciliação.
4. Teste de permissões, auditoria, concorrência e integridade referencial.
5. Aceite funcional.
6. Backup e janela de corte aprovada.
7. Troca do roteamento do módulo.
8. Monitoramento e decisão de manter ou reverter.

Não iniciar um módulo dependente antes de seus cadastros/referências estarem disponíveis e reconciliados.

### Fase 5 — Dashboard e relatórios

- Criar endpoints agregados somente após os módulos de origem estarem migrados e protegidos.
- Distinguir valores reais, ausência de dados e falha de API.
- Não exibir zero como se fosse dado real quando a fonte estiver vazia ou indisponível.
- Não chamar diferença entre contas a receber e pagar de saldo bancário.
- Definir competência, vencimento, liquidação, conciliação e regras de DRE antes de relatórios por período.

**Aceite:** métricas rastreáveis às fontes, regras aprovadas e testes de consistência.

### Fase 6 — Consolidação e encerramento da convivência

- Confirmar que todos os módulos planejados têm proprietário de dados no Shadow.
- Remover integrações temporárias e rotas antigas somente após período de estabilidade aprovado.
- Arquivar baseline, relatórios de reconciliação, evidências de testes e plano de recuperação.
- Decidir formalmente o destino do legado; não apagá-lo automaticamente.

**Aceite:** aprovação operacional, segurança revisada, recuperação comprovada e plano de encerramento documentado.

## Modelo obrigatório de ficha por módulo

Cada migração deve ter uma ficha com:

- responsável e versão do módulo;
- funcionalidades e regras do legado;
- contrato/API do Shadow;
- campos e transformação de dados;
- IDs e relacionamentos;
- fonte oficial de leitura e escrita em cada etapa;
- permissões e eventos de auditoria;
- testes unitários, integração, autorização e interface;
- contagens antes/depois e divergências;
- backup, restauração, janela de corte e gatilhos de rollback;
- evidência de aceite e data da decisão.

## Estratégia de convivência e corte

- Antes do corte, o legado continua como fonte de escrita daquele módulo.
- A carga de ensaio no Shadow é descartável e repetível.
- No corte aprovado: congelar escrita no módulo legado, gerar backup/snapshot, executar carga final, reconciliar e então direcionar o módulo ao Shadow.
- Se a reconciliação falhar, não liberar escrita no Shadow; restaurar o ponto anterior ou retornar o roteamento ao legado conforme procedimento ensaiado.
- Depois que o Shadow assumir a escrita, não reativar gravações simultâneas no legado. Um rollback deve incluir plano explícito para preservar ou reconciliar as gravações feitas após o corte.
- Não apagar dados nem desativar o legado até aprovação formal.

## Situação atual conhecida

- Existe estrutura Shadow com frontend integrado, API FastAPI e 15 domínios de serviço.
- Existem adapters PostgreSQL para os domínios e um rascunho SQL, mas não há evidência de migration aplicada ou teste com PostgreSQL real.
- O backend pode operar em memória; persistência PostgreSQL exige configuração explícita.
- Autenticação Google está implementada como fundação, mas o Client ID não foi configurado e as rotas de negócio continuam sem dependências de autenticação/autorização.
- Matriz de capacidades, onboarding e bootstrap do primeiro Admin ainda aguardam aprovação.
- Dashboard e DRE não possuem endpoints agregados completos; indicadores atuais não devem ser tratados como dados reais.
- Não há evidência de teste ponta a ponta em navegador nem de deploy completo da API Shadow.

## Próxima etapa recomendada

Retomar pela **Fase 0: inventário e matriz de equivalência do legado**, começando pelos módulos e suas dependências. O próximo artefato deve ser uma matriz módulo a módulo com funcionalidades, campos, regras, integrações, dados, estado de implementação Shadow e critérios de aceite. Não alterar o original nem iniciar importação de dados reais nesta etapa.

## Restrições

Este roteiro não aplica migrations, não cria credenciais, não conecta bancos, não publica deploy, não troca roteamento e não altera o sistema original. Qualquer corte exige aceite específico e evidência de rollback testado.
