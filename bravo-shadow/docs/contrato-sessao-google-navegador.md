# Contrato de integração da sessão Google no navegador — Bravo Shadow

**Status: especificação técnica; integração no navegador ainda não implementada.**

Este documento define a sequência mínima para ligar a sessão Google do navegador à API sem alterar a tela de login atual, sem introduzir senha local e sem abrir permissões funcionais.

## Estado confirmado no código

- A API oferece `GET /api/v1/auth/me`, protegido por Bearer token.
- O backend valida o ID token Google no servidor, incluindo assinatura, emissor, audiência e expiração, e exige `email_verified=true`.
- O principal interno só é criado depois da resolução de exatamente um cadastro ativo pelo e-mail verificado.
- O frontend Shadow ainda não possui inicialização Google Identity Services, callback de credencial nem armazenamento de sessão.
- O helper `apiRequest` ainda não envia Authorization. Não deve fabricar token nem reutilizar o legado de usuário/senha.
- GitHub Pages serve apenas arquivos estáticos e não hospeda a API FastAPI. A prévia estática deve continuar sem operações de API.

## Fluxo de integração proposto

1. Confirmar o OAuth 2.0 Web Client ID autorizado para o ambiente Shadow e as origens/redirect URIs correspondentes. Não inferir nem reutilizar um ID de outro ambiente.
2. Inicializar Google Identity Services somente após a configuração explícita do client ID.
3. Receber a credencial ID token pelo callback oficial e mantê-la apenas em memória durante a sessão da página. Não gravar ID token em localStorage, sessionStorage, URL, logs ou telemetria.
4. Enviar o token como `Authorization: Bearer <ID_TOKEN>` para `GET /api/v1/auth/me`.
5. Considerar a sessão autenticada somente após resposta válida da API. O perfil/e-mail retornados são informativos; nunca substituem a autorização no backend.
6. Em 401, limpar a credencial em memória e solicitar nova autenticação. Em 403, manter a identidade não autorizada e não tentar contornar a matriz de capacidades. Em 503, informar indisponibilidade de configuração do servidor.
7. Injetar o token em chamadas protegidas por meio de um único adaptador de API, sem duplicar lógica em cada módulo.
8. Não habilitar telas ou operações de usuários enquanto as capacidades permanecerem fechadas.

## Regras de segurança e limites

- O navegador nunca valida a assinatura do ID token como substituto da validação do backend.
- Não aceitar e-mail, perfil, subject ou status enviados pelo cliente como identidade confiável.
- Não criar fallback de login por senha nem reaproveitar `js/auth.js` legado.
- Não persistir token em armazenamento web durável. A renovação/reautenticação deve seguir o fluxo oficial do provedor.
- Não colocar credenciais em arquivos versionados, HTML, query strings ou logs.
- Não conectar produção, migrar dados reais, aplicar schema/RLS ou habilitar capacidades como parte da integração visual.
- O preview do GitHub Pages deve continuar identificando-se como estático e bloqueando chamadas à API.

## Critérios de aceite antes de implementar

- Client ID e origens do ambiente Shadow confirmados pelo responsável.
- Callback Google testado com token válido e token inválido.
- `/api/v1/auth/me` retorna 401 sem Bearer, 401 para token inválido/expirado, 403 para cadastro inexistente/inativo e 200 somente para principal validado.
- Falha de rede/servidor não deixa a interface em estado autenticado.
- Token não aparece em armazenamento persistente, URL, console ou logs.
- Testes automatizados verificam injeção de Authorization apenas quando há token em memória e garantem que o preview estático não faça chamadas.
- A tela de login permanece visualmente inalterada; não se concede nenhuma capacidade por consequência da autenticação.

## Decisões ainda necessárias

- Confirmar o Google OAuth Web Client ID e as origens permitidas do Shadow.
- Definir o domínio/API de execução do backend para o ambiente de homologação.
- Aprovar separadamente a matriz de capacidades. A autenticação bem-sucedida, por si só, não concede acesso aos módulos.

Até essas decisões serem confirmadas, a integração permanece deliberadamente não conectada.