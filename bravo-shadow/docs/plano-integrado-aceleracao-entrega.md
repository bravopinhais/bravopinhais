# Plano integrado de aceleração — Bravo Shadow

Data da revisão: 2026-11-27  
Branch-base revisada: `bravo-shadow`  
HEAD revisado: `44ea258309806df3ac5b5fa06eb04fc938754127`

## Decisão de execução

Parar de abrir novas frentes de verificações estáticas isoladas. A prioridade passa a ser fechar um fluxo integrado, automatizado e repetível, mantendo o Bravo original e qualquer banco de produção fora do caminho.

O objetivo da próxima entrega é demonstrar, em um único pipeline, que a imagem sobe, as migrations criam o schema do zero, a API inicia, a autenticação e autorização bloqueiam acessos indevidos, os módulos habilitados persistem dados sintéticos e a reconciliação confirma o resultado.

## Diagnóstico confirmado no repositório

| Área | O que existe | O que ainda impede considerar pronto |
|---|---|---|
| Frontend | Aplicação estática unificada, tema Bravo, navegação responsiva e telas de vários módulos | Nem todos os módulos têm fluxo completo conectado; módulos não migrados ainda exibem estrutura inicial |
| API | FastAPI, rotas para os módulos e cliente HTTP comum | É necessário comprovar os fluxos integrados com o backend real e persistente |
| Persistência | Driver Psycopg, adaptadores PostgreSQL e seleção explícita por configuração | O modo PostgreSQL conecta vários adaptadores; exige validar schema, permissões, RLS e CRUD em conjunto |
| Banco | Seis migrations versionadas e script de homologação local | O pipeline atual não aplica as seis migrations antes da inspeção; aplicação real ainda não comprovada |
| Autenticação | Validação server-side de identidade Google e módulo cliente | Bootstrap do frontend fica desligado sem API HTTPS Shadow validada e origem OAuth/CORS exatas |
| CI | GitHub Actions constrói o Docker, faz smoke test HTTP e executa pytest com serviço PostgreSQL | O serviço PostgreSQL do job não recebe as migrations; a consulta de catálogo atual é somente leitura |
| Preview | GitHub Pages valida/publica arquivos estáticos | Não hospeda FastAPI, banco nem autenticação; não pode ser apresentado como sistema operacional completo |
| Implantação | Dockerfile e blueprint Render preparados | Nenhum ambiente hospedado foi validado; não publicar nem conectar serviços remotos sem revisão e autorização separadas |

## Pacote único de trabalho — ordem obrigatória

### 1. Pipeline integrado de banco e aplicação
- Construir a imagem do Bravo Shadow.
- Subir PostgreSQL descartável e aguardar healthcheck.
- Aplicar, em ordem, as seis migrations da branch, desde banco vazio.
- Executar a auditoria de catálogo depois da aplicação, não antes.
- Falhar o pipeline diante de tabela, FK, índice, CHECK, RLS, policy ou privilégio divergente.
- Descartar o banco ao fim do job.

### 2. Teste ponta a ponta da API
- Iniciar a API com configuração exclusiva de teste.
- Exercitar healthcheck e OpenAPI.
- Executar CRUD integrado para cada módulo que esteja habilitado no adaptador PostgreSQL.
- Testar relações entre Plano de Contas e Financeiro, Estoque e Acertos, além das restrições de exclusão.
- Testar transações, rollback, concorrência por versão, auditoria e persistência após reiniciar a API.
- Usar exclusivamente registros sintéticos, com identificadores de teste e limpeza controlada.

### 3. Segurança e identidade
- Definir a role mínima da API e policies RLS explícitas; não usar superusuário nem BYPASSRLS como solução.
- Verificar que anon e authenticated não recebem acesso indevido.
- Validar token Google, audience, issuer, expiração, e-mail verificado, usuário cadastrado/ativo e capacidades.
- Configurar CORS e origens OAuth exatas apenas no ambiente Shadow.
- Manter o frontend sem chamadas de API enquanto a configuração HTTPS não estiver validada.

### 4. Integração real do frontend
- Ligar cada tela a rotas já existentes e a capacidades do backend.
- Priorizar o fluxo comum: autenticar, consultar, cadastrar, editar, excluir quando permitido, atualizar lista e apresentar erros.
- Onde não houver contrato/API completo, manter a tela explicitamente indisponível; não simular persistência.
- Fazer uma única rodada de revisão de responsividade, acessibilidade, mensagens e estados de carregamento após a integração.

### 5. Homologação e liberação
- Gerar relatório único com commit, versão das migrations, resultado de cada módulo e evidências do pipeline.
- Corrigir em lote as falhas encontradas e repetir o pipeline integrado.
- Só depois preparar um ambiente Shadow separado para avaliação funcional.
- Importação real e promoção ao Bravo original continuam bloqueadas até aprovação explícita, backup, reconciliação e plano de reversão.

## Critérios objetivos de conclusão

- [ ] Build Docker e smoke test passam.
- [ ] Seis migrations aplicam do zero em PostgreSQL descartável.
- [ ] Auditoria do catálogo passa após as migrations.
- [ ] CRUD integrado e persistência passam para os módulos declarados como habilitados.
- [ ] Relações, transações, rollback e auditoria passam.
- [ ] RLS, policies, grants e capacidades passam sem privilégios amplos.
- [ ] Login Google é validado no ambiente Shadow, sem segredos no frontend.
- [ ] Telas conectadas refletem dados da API; telas pendentes ficam identificadas.
- [ ] Relatório único de homologação é publicado.
- [ ] Nenhuma conexão ou escrita no Bravo original ocorreu.

## Regra de aceleração

Acelerar significa executar verificações complementares no mesmo pipeline e corrigir grupos de problemas por causa raiz. Não significa pular testes de integração, aprovar SQL não aplicado, inventar dados persistidos ou publicar um serviço incompleto.

## Limites desta revisão

Esta revisão foi estática, baseada nos arquivos da branch. Não executou Docker, PostgreSQL, migrations, pytest, OAuth ou deploy. Os itens acima são o plano de execução e os critérios de aceite, não resultados de testes já realizados.
