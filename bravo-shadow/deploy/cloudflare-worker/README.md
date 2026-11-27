# Prova isolada — Cloudflare Worker

Este pacote é uma **prova técnica de autenticação**, não é a API completa do Bravo Shadow e não está publicado.

## O que faz

- Responde `GET /api/v1/health`.
- Valida um Google ID token em `GET /api/v1/auth/me`: assinatura RS256 com chave pública Google, emissor, Client ID (audience), expiração, emissão e `email_verified`.
- Confere o e-mail em um diretório sintético configurado em `BRAVO_SHADOW_USERS`.
- Libera CORS somente para a origem exata configurada.
- Não grava dados, não usa banco, não acessa o sistema original e não cria sessão persistente.

## Limite deliberado

O diretório `BRAVO_SHADOW_USERS` é apenas uma variável de ambiente para homologação. O valor padrão é vazio (`{}`), portanto nenhum usuário é autorizado. **Não coloque e-mails reais ou cadastros de produção nessa variável.** Esta prova não substitui o cadastro interno persistente do Bravo.

O Worker também não implementa os módulos de negócio da API FastAPI. O endpoint de saúde e a validação de identidade servem somente para medir a compatibilidade do caminho de autenticação.

## Executar localmente

Requer Node.js e Wrangler. Na pasta deste pacote:

```bash
npx wrangler dev
```

A configuração usa o Client ID público já destinado ao Shadow. Nenhum Client Secret é necessário para verificar ID tokens. O diretório sintético permanece vazio por padrão.

Em outro terminal:

```bash
curl http://localhost:8787/api/v1/health
```

A resposta esperada é JSON com `status: ok` e `storage: none`.

## Publicação

Não executar `wrangler deploy` nesta etapa. Publicação exige autorização explícita, conta Cloudflare, confirmação do plano Free e revisão da origem CORS. Não adicionar cartão, ativar plano pago ou criar recursos faturáveis.

## Próximas validações

1. Executar localmente com Wrangler.
2. Testar token ausente, inválido, expirado, e-mail não verificado e usuário ausente/inativo.
3. Medir CPU no runtime Cloudflare.
4. Só então decidir se o caminho pode ser usado como gateway de autenticação.
5. Integrar o diretório real somente após definir uma fonte de dados segura e persistente, sem conexão ao banco de produção nesta prova.
