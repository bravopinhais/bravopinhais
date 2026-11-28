# Avaliação de hospedagem gratuita — Bravo Shadow

## Decisão de arquitetura

Manter o frontend estático no GitHub Pages e avaliar o Cloudflare Workers Free como endereço HTTPS para a API sombra. A avaliação não autoriza publicação, conexão com banco real, migração ou alteração do sistema original.

A documentação oficial consultada em 27/11/2026 confirma:
- FastAPI pode executar em Python Workers por meio do adaptador ASGI: https://developers.cloudflare.com/workers/languages/python/packages/fastapi/
- O plano Workers Free tem limite de 100.000 requisições por dia e 10 ms de CPU por invocação: https://developers.cloudflare.com/workers/platform/limits/
- Python Workers usa Pyodide/WebAssembly e requer atenção à compatibilidade de pacotes: https://developers.cloudflare.com/workers/languages/python/packages/

## Prova técnica criada

Pacote independente em `bravo-shadow/deploy/cloudflare-worker/`:
- `wrangler.jsonc`: configuração local do Worker, sem rota pública ou comando de publicação.
- `src/index.js`: endpoints mínimos de saúde e autenticação.
- `README.md`: instruções e limites da prova.

A prova verifica o ID token Google no servidor usando a chave pública correspondente e Web Crypto, conferindo assinatura RS256, emissor, audiência, expiração, horário de emissão e `email_verified`. Depois consulta um diretório sintético configurado por variável. O CORS aceita somente a origem configurada.

## Limites deliberados

- `BRAVO_SHADOW_USERS` começa vazio (`{}`); portanto, nenhum usuário é autorizado por padrão.
- Não cadastrar e-mails reais nessa variável nem copiar cadastros da produção.
- O Worker não implementa os módulos de negócio do backend FastAPI.
- Não há banco, armazenamento persistente, gravação externa ou conexão com o sistema original.
- Não há Client Secret OAuth no repositório; a verificação de ID token não exige esse segredo.
- O pacote ainda não foi executado no Wrangler nem medido no runtime Cloudflare.

## Próximas validações

1. Executar `npx wrangler dev` localmente e confirmar o endpoint de saúde.
2. Testar token ausente, assinatura inválida, token expirado, e-mail não verificado e usuário ausente/inativo.
3. Validar CORS com origem permitida e origem não permitida.
4. Medir o custo de CPU no runtime real e verificar compatibilidade operacional.
5. Somente depois de evidência positiva, solicitar autorização para conectar uma conta Cloudflare e publicar um Worker de homologação.

## Segredos e cobrança

- Não armazenar Client Secret OAuth, chaves de banco ou credenciais no Git.
- Não ativar plano pago, domínio pago, banco, Hyperdrive ou recurso com cobrança.
- Confirmar o plano Free e qualquer configuração de cobrança antes de publicação.

## Critérios de aprovação

A prova só será aprovada quando houver execução local reproduzível, endpoint HTTPS respondendo, validação Google no servidor, bloqueio de usuários não cadastrados/inativos, CORS restrito, testes automatizados passando e confirmação de que nenhuma dependência exige plano pago.

Até lá, o login do preview continua identificado como pendente e o sistema original permanece intocado.


## Compatibilidade com o frontend atual — verificação adicional

O bootstrap do frontend (`frontend/js/bravo-bootstrap.js`) exige que `apiBase` tenha exatamente a mesma origem HTTPS da página. Portanto, um Worker publicado em um endereço separado `*.workers.dev` não pode ser conectado diretamente pela configuração atual, mesmo que o CORS do Worker esteja correto.

Há duas arquiteturas possíveis para avaliação futura:
- manter o frontend no GitHub Pages e criar uma rota/proxy HTTPS na mesma origem para encaminhar `/api/*` ao backend; ou
- aprovar uma alteração explícita no bootstrap para API em origem HTTPS separada, mantendo allowlist CORS exata e validação de destino.

Nenhuma dessas opções está implementada ou autorizada. A segunda alternativa não resolve, por si só, a ausência dos módulos FastAPI no Worker. A prova de autenticação permanece isolada e não deve ser conectada ao frontend como se fosse a API completa.
