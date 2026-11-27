# Guia de homologação gratuita — Bravo Shadow

Data: 27/11/2026

## Arquitetura escolhida para preparação

- **Render Free:** um único serviço Docker executa FastAPI e serve `frontend/` na mesma origem HTTPS. Isso evita separar UI/API e não exige CORS entre elas.
- **Supabase Free:** PostgreSQL isolado do Shadow, sem usar autenticação Supabase. O login continua sendo Google Identity Services + vínculo com o cadastro interno Bravo.
- **Git:** branch `bravo-shadow` exclusivamente. O Blueprint aponta para essa branch e `autoDeployTrigger: off` para impedir deploy automático a cada commit.
- **Produção:** nenhum domínio, banco, credencial ou serviço de produção deve ser conectado.

## Arquivo preparado

`render.yaml` define um único Web Service Docker gratuito na região Ohio, `rootDir: bravo-shadow`, health check `/api/v1/health`, PostgreSQL obrigatório e deploy automático desligado. O primeiro deploy somente ocorre se alguém conectar o repositório e confirmar a criação do Blueprint no painel Render.

`BRAVO_DATABASE_URL` é `sync: false`: deve ser informada diretamente no cofre de variáveis do Render, nunca no Git. O valor de `BRAVO_CORS_ORIGINS` fica vazio porque frontend e API serão servidos pela mesma origem.

## Configuração manual necessária (não executada)

1. Criar/selecionar uma conta Render no plano Free e conectar o repositório com acesso somente à branch `bravo-shadow`, se a permissão permitir.
2. No painel Render, usar o Blueprint `bravo-shadow/render.yaml`. Conferir antes de confirmar que o serviço é `bravo-shadow-homologacao`, plano Free, região Ohio, branch `bravo-shadow` e auto deploy desligado.
3. Criar um projeto Supabase no plano Free, nomeado claramente como homologação Bravo Shadow, em região próxima disponível. Não ativar Supabase Auth.
4. Guardar a connection string PostgreSQL desse projeto e inserir apenas no secret `BRAVO_DATABASE_URL` do Render. Não compartilhar a URL em chat ou commit.
5. Confirmar `BRAVO_STORAGE_BACKEND=postgres` e `GOOGLE_CLIENT_ID` no Render. Não inserir credenciais de produção.
6. Após criação manual do serviço, copiar a origem HTTPS `onrender.com` gerada e adicioná-la às origens JavaScript autorizadas do OAuth Client Google. Não usar o domínio de produção.
7. Manter CORS vazio enquanto frontend e API estiverem na mesma origem. Se futuramente forem separados, configurar somente a origem HTTPS exata do frontend.
8. Antes de qualquer uso, revisar e aplicar exclusivamente as migrations Shadow no banco vazio, confirmar schema isolado e verificar `/api/v1/health`.

## Limitações do plano gratuito

- Render Free suspende o processo após 15 minutos sem tráfego; o primeiro acesso posterior pode levar cerca de um minuto para acordar.
- Render Free tem limite de horas mensais compartilhado pelo workspace e armazenamento de arquivos efêmero. Não guardar anexos no disco local.
- Supabase Free fornece 500 MB por projeto, não inclui backups automáticos e pode pausar o projeto após uma semana de baixa atividade.
- A combinação é somente para desenvolvimento/homologação e demonstração com dados sintéticos. Não é adequada para operação real, dados pessoais de moradores, documentos ou rotina condominial.

## Critérios para liberar a próxima fase

- Origem HTTPS Shadow independente confirmada.
- Banco PostgreSQL vazio e exclusivo, com backups/exportação definidos antes de qualquer dado não sintético.
- Google OAuth com origem Shadow autorizada e callback/validação conferidos.
- Migrations revisadas e aplicadas somente no schema Shadow.
- Health check, autenticação, autorização e persistência validados no ambiente isolado.

## Estado desta entrega

- Blueprint e guia foram versionados na branch `bravo-shadow`.
- Nenhuma conta, projeto Supabase, serviço Render, banco ou deploy foi criado.
- Nenhuma migration foi aplicada.
- Nenhuma credencial ou dado real foi adicionado.
- O deploy automático está desligado no Blueprint.
