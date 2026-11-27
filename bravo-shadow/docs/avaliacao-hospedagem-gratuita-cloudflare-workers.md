# Avaliação de hospedagem gratuita — Bravo Shadow

## Decisão de arquitetura

Manter o frontend estático no GitHub Pages e avaliar o Cloudflare Workers Free como endereço HTTPS para a API sombra. A avaliação não autoriza publicação, conexão com banco real, migração ou alteração do sistema original.

A documentação oficial do Cloudflare informa suporte a FastAPI em Python Workers por meio de ASGI e disponibiliza plano Free com limite de 100.000 requisições por dia e 10 ms de CPU por invocação:
- https://developers.cloudflare.com/workers/languages/python/packages/fastapi/
- https://developers.cloudflare.com/workers/platform/pricing/
- https://developers.cloudflare.com/workers/platform/limits/

## Compatibilidade que ainda precisa ser provada

O backend atual não deve ser publicado diretamente sem uma prova de compatibilidade. As dependências atuais incluem:

- `fastapi`: há exemplo oficial de execução em Python Workers.
- `google-auth[requests]`: precisa ser verificada quanto a dependências, transporte HTTP e suporte de pacotes Pyodide.
- `psycopg[binary]`: não deve ser usado no Worker; o modo de armazenamento deve permanecer `memory` durante a prova e nenhuma URL de banco deve ser configurada.
- `uvicorn[standard]`: Python Workers fornece seu próprio adaptador ASGI; Uvicorn não deve ser presumido como necessário no runtime.

Python Workers executa sobre Pyodide/WebAssembly. A documentação limita pacotes a bibliotecas puras Python, PyEmscripten ou incluídas no Pyodide. O plano Free limita CPU a 10 ms por chamada. A validação criptográfica do ID token e a busca das chaves públicas do Google precisam ser medidas no runtime real antes de aprovar essa hospedagem.

## Prova técnica isolada — sequência

1. Criar um pacote de implantação próprio em `bravo-shadow/deploy/cloudflare-worker/`, sem alterar a API principal.
2. Implementar somente endpoints mínimos de saúde e autenticação, mantendo o contrato HTTP compatível com o frontend.
3. Usar validação de token Google no servidor; nunca aceitar e-mail informado pelo navegador como prova de identidade.
4. Conferir assinatura, emissor, audiência, expiração e `email_verified`; em seguida consultar cadastro interno ativo.
5. Configurar CORS para a origem exata do preview Shadow, sem curingas.
6. Usar apenas dados sintéticos e armazenamento em memória; sem banco de produção e sem gravações externas.
7. Executar testes locais e de integração, inclusive token inválido, token expirado, e-mail não verificado, usuário inexistente/inativo, CORS e limite de CPU.
8. Somente depois de evidência positiva, solicitar autorização para conectar uma conta Cloudflare e publicar um Worker de homologação.

## Segredos e cobrança

- Não armazenar Client Secret OAuth, chaves de banco ou credenciais no Git.
- O Client ID público pode ser configurado como variável não secreta; segredos, se futuramente necessários, devem usar o mecanismo de secrets do provedor.
- Não ativar plano pago, domínio pago, banco, Hyperdrive ou recurso com cobrança.
- Confirmar que a conta permanece no plano Free e que não existe método de pagamento/upgrade acionado antes de qualquer publicação.

## Critérios de aprovação

A prova só será considerada aprovada quando houver: build/deploy de teste reproduzível, endpoint HTTPS respondendo, autenticação Google verificada no servidor, bloqueio de usuários não cadastrados/inativos, CORS restrito, testes automatizados passando e confirmação de que nenhuma dependência exige plano pago.

Até lá, o login do preview continua identificado como pendente e o sistema original permanece intocado.
